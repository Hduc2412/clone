"""Conservative chat intake, without an extra paid model call.

Consultation context is embedded with the candidate so one versioned write
updates both. Preferences remain the canonical matching input for compatibility.
Unrecognised statements stay as quotations, never guessed personal attributes.
"""
import re

from pymongo.errors import DuplicateKeyError

from app.core.codes import PREFIX_PROFILE, new_code
from app.core.phone import normalize_vietnamese_phone
from app.db import candidate_profiles as profiles
from app.db.common import now
from app.matching import catalog


def extract_assertions(text: str) -> tuple[dict, dict, dict]:
    fields, preferences, evidence = {}, {}, {}
    # Deliberately reject questions, hypotheticals and multi-clause inference.
    for clause in re.split(r"[,;\n.!]", text):
        clause = clause.strip()
        if not clause or "?" in clause:
            continue
        match = re.fullmatch(r"(?:tôi|mình|em) (?:đã có|có chứng chỉ|đã đạt) (N[1-5])", clause, re.I)
        if match:
            fields["japanese_level"] = match[1].upper()
            evidence["japanese_level"] = clause
        match = re.fullmatch(r"(?:tôi|mình|em) (?:muốn|mong muốn) (?:đi|làm việc (?:ở|tại)) ([\w -]+)", clause, re.I)
        if match:
            province = catalog.normalize_prefecture(match[1])
            if province:
                preferences["desired_prefecture"] = province
                preferences["desired_region_group"] = catalog.region_for_prefecture(province)
                evidence.update({key: clause for key in preferences})
        match = re.fullmatch(r"(?:tôi|mình|em) tên (?:là )?([\wÀ-ỹ -]{2,100})", clause, re.I)
        if match and 1 <= len(match[1].split()) <= 5:
            # Only a standalone introduction, not "tôi tên Nam muốn đi ...".
            if not re.search(r"\b(muốn|học|có|đi|là|không)\b", match[1], re.I):
                fields["full_name"] = match[1].strip()
                evidence["full_name"] = clause
        match = re.fullmatch(r"(?:số điện thoại|sđt) (?:của )?(?:tôi|mình|em)(?: là|:) ?([+\d -]+)", clause, re.I)
        if match:
            try:
                fields["phone"] = normalize_vietnamese_phone(match[1])
                evidence["phone"] = clause
            except ValueError:
                pass
    return fields, preferences, evidence


async def capture(session_id: str, text: str, intent: str) -> None:
    fields, preferences, evidence = extract_assertions(text)
    for _ in range(3):
        profile = await profiles.get_by_session(session_id)
        if profile is None:
            try:
                profile = await profiles.create_profile({
                    "code": new_code(PREFIX_PROFILE), "session_id": session_id,
                })
            except DuplicateKeyError:
                continue
        merged_fields, changed_fields = profiles.merge_section(
            profile.get("fields"), fields, source="chat", allowed=profiles.FIELD_KEYS, evidence=evidence,
        )
        merged_preferences, changed_preferences = profiles.merge_section(
            profile.get("preferences"), preferences, source="chat", allowed=profiles.PREFERENCE_KEYS, evidence=evidence,
        )
        context = dict(profile.get("consultation") or {})
        conflicts = list(context.get("conflicts") or [])
        for section, incoming in (("fields", fields), ("preferences", preferences)):
            for key, value in incoming.items():
                old = (profile.get(section) or {}).get(key)
                if old and old.get("value") != value:
                    conflicts.append({"field": key, "previous": old["value"], "suggested": value,
                                      "evidence": evidence.get(key), "source": "chat"})
        context["conflicts"] = conflicts[-20:]
        messages = list(context.get("recent_messages") or [])
        messages.append({"content": text, "intent": intent, "recorded_at": now(), "source": "chat"})
        context["recent_messages"] = messages[-20:]
        context["last_intent"] = intent
        context["updated_at"] = now()
        changed = changed_fields + changed_preferences
        updated = await profiles.apply_changes(
            session_id, expected_version=profile.get("version", 1),
            fields=merged_fields, preferences=merged_preferences,
            history=profiles.history_entry(profile, "chat", "Tiếp nhận hội thoại"),
            # A machine must never silently confirm newly extracted values.
            status=profiles.STATUS_EXTRACTED if changed else None,
            consultation=context,
        )
        if updated is not None:
            return
    raise RuntimeError("Concurrent profile updates; chat intake was not saved")
