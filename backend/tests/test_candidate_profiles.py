"""Kiểm thử hồ sơ ứng viên: gộp theo nguồn, khóa phiên bản và phân quyền.

Trọng tâm là quy tắc ưu tiên nguồn `staff > user_confirmed > cv > chat`. Đây là
thứ giữ cho bản đọc CV lần hai không xóa mất giá trị ứng viên đã tự sửa, và giữ
cho một người bất kỳ không tự khai mình là nhân viên để đè lên dữ liệu đã duyệt.
"""
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException, Request
from pydantic import ValidationError
from pymongo.errors import DuplicateKeyError

from app.api.profiles import (
    AssignmentRequest,
    FieldsPayload,
    PreferencesPayload,
    ProfileCreateRequest,
    ProfilePatchRequest,
    assign_profile,
    confirm_profile,
    create_profile,
    get_profile,
    patch_profile,
    admin_profile_meta,
    profile_detail,
    profile_meta,
    profiles,
    router,
    update_profile,
)
from app.core.timeutil import local_today
from app.db import candidate_profiles as store


def http_request() -> Request:
    return Request({"type": "http", "headers": [], "client": ("127.0.0.1", 12345)})


ADMIN = {"email": "admin@example.com", "full_name": "Quản trị", "role": "admin"}
MANAGER = {"email": "manager@example.com", "full_name": "Quản lý", "role": "manager"}
CONSULTANT = {"email": "tu.van@example.com", "full_name": "Tư vấn", "role": "consultant"}

SESSION = "phien-ung-vien-0001"


def profile_doc(**overrides) -> dict:
    document = {
        "code": "UV-ABC123",
        "session_id": SESSION,
        "status": store.STATUS_CONFIRMED,
        "version": 1,
        "fields": {
            "full_name": store.cell("Nguyễn Văn An", "user_confirmed"),
            "japanese_level": store.cell("N4", "user_confirmed"),
        },
        "preferences": {},
        "history": [],
        "assigned_to": None,
        "lead_code": None,
        "phone_normalized": None,
    }
    document.update(overrides)
    return document


class CellAndMergeTests(unittest.TestCase):
    """Phần thuần: gộp giá trị không cần chạm database."""

    def test_cell_carries_source_and_default_confidence(self):
        self.assertEqual(
            store.cell("N3", "cv", evidence="Trình độ: N3"),
            {"value": "N3", "source": "cv", "confidence": 0.9, "evidence": "Trình độ: N3"},
        )

    def test_unknown_source_gets_a_cautious_confidence(self):
        self.assertEqual(store.cell("x", "nguon_la")["confidence"], 0.5)

    def test_merge_reports_only_the_keys_that_really_changed(self):
        existing = {"full_name": store.cell("An", "chat")}
        merged, changed = store.merge_section(
            existing,
            {"full_name": "An", "japanese_level": "N4"},
            source="chat",
            allowed=store.FIELD_KEYS,
        )
        self.assertEqual(changed, ["japanese_level"])
        self.assertEqual(merged["full_name"]["source"], "chat")

    def test_cv_never_overwrites_what_the_candidate_confirmed(self):
        """Đọc CV lần hai không được xóa thứ ứng viên đã tự sửa."""
        existing = {"japanese_level": store.cell("N4", "user_confirmed")}
        merged, changed = store.merge_section(
            existing, {"japanese_level": "N3"}, source="cv", allowed=store.FIELD_KEYS
        )
        self.assertEqual(merged["japanese_level"]["value"], "N4")
        self.assertEqual(changed, [])

    def test_staff_overwrites_the_candidate(self):
        existing = {"japanese_level": store.cell("N4", "user_confirmed")}
        merged, changed = store.merge_section(
            existing, {"japanese_level": "N3"}, source="staff", allowed=store.FIELD_KEYS
        )
        self.assertEqual(merged["japanese_level"]["value"], "N3")
        self.assertEqual(changed, ["japanese_level"])

    def test_staff_resaving_the_same_value_keeps_the_original_source_and_evidence(self):
        """Nhân viên gửi lại đúng giá trị cũ thì ô không đổi — cả nguồn lẫn trích dẫn.

        Đây là biểu mẫu sửa hồ sơ: đổi một ô rồi lưu thì form gửi lại toàn bộ.
        Nếu "staff gửi lại giá trị cũ" bị coi là thay đổi, mọi trường ứng viên
        tự xác nhận biến thành "nhân viên nhập" và mọi đoạn trích từ CV mất sạch.
        """
        existing = {
            "education_level": store.cell("cao_dang", "cv", evidence="Cao đẳng Điều dưỡng"),
        }
        merged, changed = store.merge_section(
            existing, {"education_level": "cao_dang"}, source="staff", allowed=store.FIELD_KEYS
        )
        self.assertEqual(changed, [])
        self.assertEqual(merged["education_level"]["source"], "cv")
        self.assertEqual(merged["education_level"]["evidence"], "Cao đẳng Điều dưỡng")

    def test_confirmation_promotes_the_source_but_keeps_the_evidence(self):
        """Xác nhận nâng nguồn nghe-trong-hội-thoại lên ứng-viên-xác-nhận, giữ câu gốc."""
        existing = {"japanese_level": store.cell("N4", "chat", evidence="tôi đã có N4")}
        merged, changed = store.merge_section(
            existing,
            {"japanese_level": "N4"},
            source="user_confirmed",
            allowed=store.FIELD_KEYS,
            promote_on_equal=True,
        )
        self.assertEqual(changed, ["japanese_level"])
        self.assertEqual(merged["japanese_level"]["source"], "user_confirmed")
        self.assertEqual(merged["japanese_level"]["evidence"], "tôi đã có N4")

    def test_same_source_may_correct_itself(self):
        existing = {"full_name": store.cell("Nguyen Van An", "user_confirmed")}
        merged, changed = store.merge_section(
            existing,
            {"full_name": "Nguyễn Văn An"},
            source="user_confirmed",
            allowed=store.FIELD_KEYS,
        )
        self.assertEqual(merged["full_name"]["value"], "Nguyễn Văn An")
        self.assertEqual(changed, ["full_name"])

    def test_empty_values_are_skipped_not_stored_as_blank(self):
        """Trường vắng mặt nghĩa là chưa rõ, không phải là một câu trả lời rỗng."""
        merged, changed = store.merge_section(
            {}, {"full_name": "", "major": None}, source="cv", allowed=store.FIELD_KEYS
        )
        self.assertEqual(merged, {})
        self.assertEqual(changed, [])

    def test_a_preference_key_is_rejected_by_the_fields_section(self):
        """Hai mục tách nhau nên một nguyện vọng không lọt vào chỗ dùng để loại đơn."""
        with self.assertRaises(ValueError):
            store.merge_section(
                {},
                {"desired_prefecture": "Tokyo"},
                source="staff",
                allowed=store.FIELD_KEYS,
            )

    def test_the_two_sections_do_not_share_any_key(self):
        self.assertEqual(store.FIELD_KEYS & store.PREFERENCE_KEYS, frozenset())

    def test_chua_hoc_counts_as_an_answer_for_the_required_check(self):
        profile = profile_doc(
            fields={
                "full_name": store.cell("An", "chat"),
                "japanese_level": store.cell("chua_hoc", "chat"),
            }
        )
        self.assertEqual(store.missing_required(profile), [])

    def test_missing_required_lists_what_is_still_needed(self):
        self.assertEqual(
            store.missing_required({"fields": {}}), ["full_name", "japanese_level"]
        )

    def test_public_view_hides_internal_columns(self):
        view = store.public_view(profile_doc(assigned_to="a@b.c", lead_code="KH-1"))
        for hidden in ("history", "assigned_to", "lead_code", "phone_normalized"):
            self.assertNotIn(hidden, view)
        self.assertIn("fields", view)

    def test_history_entry_snapshots_the_version_before_the_change(self):
        entry = store.history_entry(profile_doc(version=3), "admin@example.com", "sửa: phone")
        self.assertEqual(entry["version"], 3)
        self.assertEqual(entry["changed_by"], "admin@example.com")


class PayloadValidationTests(unittest.TestCase):
    def test_labels_and_codes_are_both_accepted(self):
        payload = FieldsPayload(
            gender="Nữ", education_level="Cao đẳng", japanese_level="N4 trở lên"
        )
        self.assertEqual(payload.gender, "nu")
        self.assertEqual(payload.education_level, "cao_dang")
        self.assertEqual(payload.japanese_level, "N4")

    def test_an_invalid_catalog_value_is_refused(self):
        with self.assertRaises(ValidationError):
            FieldsPayload(japanese_level="N9")

    def test_a_birth_year_too_recent_is_refused(self):
        with self.assertRaises(ValidationError):
            FieldsPayload(birth_year=local_today().year - 3)

    def test_phone_is_normalized(self):
        self.assertEqual(FieldsPayload(phone="+84 971 716 939").phone, "0971716939")

    def test_region_is_derived_from_the_desired_prefecture(self):
        self.assertEqual(PreferencesPayload(desired_prefecture="Tokyo").desired_region_group, "kanto")

    def test_the_derived_region_actually_reaches_the_profile(self):
        """Suy ra vùng mà để nó bị `exclude_unset` loại thì coi như không suy.

        Hậu quả: ứng viên muốn Tokyo sẽ chấm một đơn ở Kanagawa (cùng vùng Kantō,
        đáng +25) ngang bằng một đơn ở Fukuoka.
        """
        payload = PreferencesPayload(desired_prefecture="Tokyo")
        self.assertEqual(
            payload.model_dump(exclude_unset=True)["desired_region_group"], "kanto"
        )

    def test_an_explicit_region_is_not_overwritten_by_the_prefecture(self):
        payload = PreferencesPayload(desired_prefecture="Tokyo", desired_region_group="Kansai")
        self.assertEqual(payload.desired_region_group, "kansai")

    def test_an_unknown_key_is_rejected_rather_than_ignored(self):
        with self.assertRaises(ValidationError):
            FieldsPayload(luong_mong_muon=200000)

    def test_source_can_never_be_supplied_by_the_client(self):
        """Nếu nhận `source` từ client thì ai cũng tự khai được là nhân viên."""
        for model in (FieldsPayload, PreferencesPayload, ProfileCreateRequest, ProfilePatchRequest):
            self.assertNotIn("source", model.model_fields)
        with self.assertRaises(ValidationError):
            ProfileCreateRequest(session_id=SESSION, source="staff")

    def test_session_id_must_look_like_a_session(self):
        with self.assertRaises(ValidationError):
            ProfileCreateRequest(session_id="ngắn")


class PublicProfileApiTests(unittest.IsolatedAsyncioTestCase):
    async def test_meta_lists_the_catalogs_the_form_needs(self):
        meta = await profile_meta()
        self.assertEqual(len(meta["prefectures"]), 47)
        self.assertEqual(meta["required_fields"], list(store.REQUIRED_FOR_CONFIRM))
        self.assertTrue(meta["japanese_levels"])

    async def test_manual_entry_is_confirmed_immediately(self):
        with patch.object(store, "create_profile", new=AsyncMock(side_effect=lambda d: d)):
            result = await create_profile(
                ProfileCreateRequest(
                    session_id=SESSION,
                    fields={"full_name": "Nguyễn Văn An", "japanese_level": "N4"},
                ),
                http_request(),
            )
        self.assertEqual(result["status"], store.STATUS_CONFIRMED)
        self.assertEqual(result["fields"]["full_name"]["source"], "user_confirmed")
        self.assertEqual(result["missing_required"], [])

    async def test_an_extracted_profile_waits_for_the_candidate_to_review(self):
        with patch.object(store, "create_profile", new=AsyncMock(side_effect=lambda d: d)):
            result = await create_profile(
                ProfileCreateRequest(
                    session_id=SESSION, mode="extracted", fields={"full_name": "An"}
                ),
                http_request(),
            )
        self.assertEqual(result["status"], store.STATUS_EXTRACTED)
        self.assertIsNone(result["confirmed_at"])

    async def test_a_second_profile_for_the_same_session_is_refused(self):
        with patch.object(store, "create_profile", new=AsyncMock(side_effect=DuplicateKeyError("x"))):
            with self.assertRaises(HTTPException) as caught:
                await create_profile(ProfileCreateRequest(session_id=SESSION), http_request())
        self.assertEqual(caught.exception.status_code, 409)

    async def test_reading_a_session_without_a_profile_gives_404(self):
        with patch.object(store, "get_by_session", new=AsyncMock(return_value=None)):
            with self.assertRaises(HTTPException) as caught:
                await get_profile(SESSION)
        self.assertEqual(caught.exception.status_code, 404)

    async def test_the_public_response_never_leaks_the_assignment(self):
        with patch.object(
            store, "get_by_session", new=AsyncMock(return_value=profile_doc(assigned_to="a@b.c"))
        ):
            result = await get_profile(SESSION)
        self.assertNotIn("assigned_to", result)
        self.assertEqual(result["labels"]["japanese_level"], "N4")

    async def test_patching_writes_user_confirmed_and_bumps_the_version(self):
        applied = {}

        async def fake_apply(session_id, **kwargs):
            applied.update(kwargs)
            return profile_doc(version=2, fields=kwargs["fields"])

        with patch.object(store, "get_by_session", new=AsyncMock(return_value=profile_doc())), patch.object(
            store, "apply_changes", new=AsyncMock(side_effect=fake_apply)
        ):
            result = await patch_profile(
                SESSION, ProfilePatchRequest(fields={"birth_year": 2000}), http_request()
            )
        self.assertEqual(applied["expected_version"], 1)
        self.assertEqual(result["fields"]["birth_year"]["source"], "user_confirmed")

    async def test_a_patch_that_changes_nothing_does_not_create_a_version(self):
        write = AsyncMock()
        with patch.object(store, "get_by_session", new=AsyncMock(return_value=profile_doc())), patch.object(
            store, "apply_changes", new=write
        ):
            result = await patch_profile(
                SESSION, ProfilePatchRequest(fields={"full_name": "Nguyễn Văn An"}), http_request()
            )
        write.assert_not_awaited()
        self.assertEqual(result["version"], 1)

    async def test_two_tabs_editing_at_once_lose_the_race_loudly(self):
        """Khóa lạc quan: tab sau nhận 409 chứ không âm thầm đè lên tab trước."""
        with patch.object(store, "get_by_session", new=AsyncMock(return_value=profile_doc())), patch.object(
            store, "apply_changes", new=AsyncMock(return_value=None)
        ):
            with self.assertRaises(HTTPException) as caught:
                await patch_profile(
                    SESSION,
                    ProfilePatchRequest(fields={"birth_year": 2000}, expected_version=1),
                    http_request(),
                )
        self.assertEqual(caught.exception.status_code, 409)

    async def test_confirming_an_incomplete_profile_says_what_is_missing(self):
        with patch.object(
            store, "get_by_session", new=AsyncMock(return_value=profile_doc(fields={}))
        ):
            with self.assertRaises(HTTPException) as caught:
                await confirm_profile(SESSION, http_request())
        self.assertEqual(caught.exception.status_code, 409)
        self.assertEqual(
            caught.exception.detail["missing"], ["full_name", "japanese_level"]
        )

    async def test_confirming_sets_the_status_and_the_timestamp(self):
        applied = {}

        async def fake_apply(session_id, **kwargs):
            applied.update(kwargs)
            return profile_doc(version=2, status=store.STATUS_CONFIRMED)

        with patch.object(
            store,
            "get_by_session",
            new=AsyncMock(return_value=profile_doc(status=store.STATUS_EXTRACTED)),
        ), patch.object(store, "apply_changes", new=AsyncMock(side_effect=fake_apply)):
            result = await confirm_profile(SESSION, http_request())
        self.assertEqual(applied["status"], store.STATUS_CONFIRMED)
        self.assertIsNotNone(applied["confirmed_at"])
        self.assertEqual(result["labels"]["status"], "Đã xác nhận")

    async def test_confirming_twice_is_harmless(self):
        write = AsyncMock()
        with patch.object(store, "get_by_session", new=AsyncMock(return_value=profile_doc())), patch.object(
            store, "apply_changes", new=write
        ):
            result = await confirm_profile(SESSION, http_request())
        write.assert_not_awaited()
        self.assertEqual(result["status"], store.STATUS_CONFIRMED)


class StaffProfileApiTests(unittest.IsolatedAsyncioTestCase):
    async def test_a_consultant_only_sees_their_own_profiles(self):
        captured = {}

        async def fake_list(query, *, limit):
            captured.update(query)
            return []

        with patch.object(store, "list_profiles", new=AsyncMock(side_effect=fake_list)):
            await profiles(status=None, assigned_to=None, lead_code=None, limit=100, current_user=CONSULTANT)
        self.assertEqual(captured["assigned_to"], CONSULTANT["email"])

    async def test_a_manager_sees_everything(self):
        captured = {"touched": False}

        async def fake_list(query, *, limit):
            captured["query"] = query
            return []

        with patch.object(store, "list_profiles", new=AsyncMock(side_effect=fake_list)):
            await profiles(status=None, assigned_to=None, lead_code=None, limit=100, current_user=MANAGER)
        self.assertNotIn("assigned_to", captured["query"])

    async def test_a_consultant_cannot_open_someone_elses_profile(self):
        other = profile_doc(assigned_to="nguoi.khac@example.com")
        with patch.object(store, "get_by_code", new=AsyncMock(return_value=other)):
            with self.assertRaises(HTTPException) as caught:
                await profile_detail("UV-ABC123", current_user=CONSULTANT)
        self.assertEqual(caught.exception.status_code, 403)

    async def test_staff_edits_are_written_with_the_staff_source(self):
        applied = {}

        async def fake_apply(session_id, **kwargs):
            applied.update(kwargs)
            return profile_doc(version=2, fields=kwargs["fields"])

        with patch.object(store, "get_by_code", new=AsyncMock(return_value=profile_doc())), patch.object(
            store, "apply_changes", new=AsyncMock(side_effect=fake_apply)
        ), patch("app.api.profiles.audit_action", new=AsyncMock()) as audit:
            result = await update_profile(
                "UV-ABC123",
                ProfilePatchRequest(fields={"japanese_level": "N3"}),
                http_request(),
                current_user=ADMIN,
            )
        self.assertEqual(result["fields"]["japanese_level"]["source"], "staff")
        self.assertEqual(audit.await_args.kwargs["details"]["changed_fields"], ["japanese_level"])

    async def test_the_staff_form_reads_the_same_catalog_as_the_candidate_form(self):
        """Hai biểu mẫu ghi vào cùng những trường, nên phải thấy cùng lựa chọn.

        Hai bản danh mục chép tay sẽ lệch nhau ngay lần đầu thêm một mức tiếng
        Nhật, và nhân viên sẽ không nhập được đúng thứ ứng viên chọn.
        """
        self.assertEqual(await admin_profile_meta(), await profile_meta())

    def test_profiles_meta_does_not_fall_into_the_code_route(self):
        """`/profiles/meta` phải khớp handler danh mục, không phải `/{code}`.

        FastAPI khớp theo thứ tự khai báo. Đặt `/meta` sau `/{code}` thì mọi lần
        mở biểu mẫu sửa hồ sơ đều nhận 404 "không tìm thấy hồ sơ", và lỗi ấy đọc
        như dữ liệu hỏng chứ không như một route đặt nhầm chỗ.
        """
        matched = next(
            route
            for route in router.routes
            if route.path_regex.match("/profiles/meta") and "GET" in route.methods
        )
        self.assertEqual(matched.endpoint, admin_profile_meta)

    async def test_assigning_an_unknown_profile_gives_404(self):
        with patch("app.api.profiles.validate_assignee", new=AsyncMock(return_value=None)), patch.object(
            store, "set_assignment", new=AsyncMock(return_value=None)
        ):
            with self.assertRaises(HTTPException) as caught:
                await assign_profile(
                    "UV-KHONG-CO", AssignmentRequest(), http_request(), current_user=ADMIN
                )
        self.assertEqual(caught.exception.status_code, 404)

    async def test_assignment_is_recorded_in_the_audit_log(self):
        with patch(
            "app.api.profiles.validate_assignee", new=AsyncMock(return_value=CONSULTANT["email"])
        ), patch.object(
            store,
            "set_assignment",
            new=AsyncMock(return_value=profile_doc(assigned_to=CONSULTANT["email"])),
        ), patch("app.api.profiles.audit_action", new=AsyncMock()) as audit:
            await assign_profile(
                "UV-ABC123",
                AssignmentRequest(assigned_to=CONSULTANT["email"]),
                http_request(),
                current_user=MANAGER,
            )
        self.assertEqual(audit.await_args.args[1], "candidate_profile.assigned")


if __name__ == "__main__":
    unittest.main()
