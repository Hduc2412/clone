"""Điều phối việc đối chiếu hồ sơ với danh mục đơn hàng.

Tầng này lo phần có vào ra dữ liệu: lấy danh mục đơn, tính dấu vân tay, tra bộ
nhớ đệm, gọi bộ đối chiếu thuần, rồi ghi nhật ký. Bản thân phép tính nằm trọn
trong `app/matching/engine.py` và không biết gì về database.
"""
import hashlib
from datetime import date, timedelta
from operator import itemgetter
from typing import Any, Sequence

from app.core.codes import PREFIX_RECOMMENDATION, new_code
from app.core.timeutil import local_today, utc_now
from app.db import job_orders, recommendation_logs
from app.matching import engine, explain
from app.matching.weights import load_weights


# Kho đơn đem đối chiếu là **mọi đơn đã từng công khai**, không dùng bộ lọc công
# khai. Phải giữ lại đơn hết hạn và đơn tạm dừng, nếu không nhật ký giới thiệu
# không có gì để chứng minh bộ lọc điều kiện đã hoạt động. Đơn còn ở trạng thái
# nháp thì không bao giờ được chào cho ai nên không vào kho.
POOL_QUERY: dict[str, Any] = {"published": True}

# Trong mười phút, bốn yếu tố đầu vào đã được chứng minh là giống hệt nhau, nên
# chạy lại chắc chắn ra cùng kết quả. Quá mốc đó thì chạy lại, để ngày tháng đổi
# qua nửa đêm kéo theo tiêu chí hạn nộp cũng được tính lại.
CACHE_TTL_SECONDS = 600

DEFAULT_TOP_N = 5


def orders_fingerprint(orders: Sequence[dict[str, Any]]) -> str:
    """Dấu vân tay của danh mục đơn.

    Sắp theo mã trước khi băm, để thứ tự MongoDB trả về không làm đổi dấu vân tay.
    Có kèm `updated_at` nên sửa một điều kiện của đơn là bộ nhớ đệm mất hiệu lực
    ngay, không còn dùng lại kết quả tính theo điều kiện cũ.
    """
    parts = []
    for order in sorted(orders, key=itemgetter("code")):
        updated = order.get("updated_at")
        stamp = updated.isoformat() if hasattr(updated, "isoformat") else str(updated)
        parts.append(f"{order['code']}|{stamp}")
    digest = hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()
    return f"sha256:{digest[:16]}"


async def load_pool() -> list[dict[str, Any]]:
    return await job_orders.list_job_orders(dict(POOL_QUERY), limit=500)


async def run_matching(
    profile: dict[str, Any],
    *,
    trigger: str,
    actor_email: str | None = None,
    as_of: date | None = None,
    force: bool = False,
) -> tuple[dict[str, Any], bool]:
    """Chạy đối chiếu và ghi nhật ký. Trả về bản ghi và cờ cho biết có dùng lại không."""
    reference_date = as_of or local_today()
    weights = load_weights()
    pool = await load_pool()
    fingerprint = orders_fingerprint(pool)

    if not force:
        cached = await recommendation_logs.find_cached(
            profile_code=profile["code"],
            profile_version=profile.get("version", 1),
            orders_fingerprint=fingerprint,
            weights_fingerprint=weights.fingerprint,
            since=utc_now() - timedelta(seconds=CACHE_TTL_SECONDS),
        )
        if cached is not None:
            return cached, True

    facts = engine.build_facts(profile, reference_date)
    result = engine.match_orders(pool, facts, weights=weights, as_of=reference_date)
    payload = result.as_dict()

    document = {
        "code": new_code(PREFIX_RECOMMENDATION),
        "profile_code": profile["code"],
        "profile_version": profile.get("version", 1),
        "session_id": profile.get("session_id"),
        "assigned_to": profile.get("assigned_to"),
        "application_code": None,
        "orders_fingerprint": fingerprint,
        "weights_fingerprint": weights.fingerprint,
        "weights_version": weights.version,
        "engine_version": payload["engine_version"],
        "as_of": payload["as_of"],
        "pool_query": dict(POOL_QUERY),
        "total_considered": payload["total_considered"],
        "eligible_count": payload["eligible_count"],
        "top_codes": [item.code for item in result.top(DEFAULT_TOP_N)],
        "missing_info": payload["missing_info"],
        "items": payload["items"],
        "trigger": trigger,
        "actor_email": actor_email,
    }
    return await recommendation_logs.create_log(document), False


def to_public_payload(log: dict[str, Any], *, limit: int) -> dict[str, Any]:
    """Bản dành cho ứng viên.

    Chỉ gồm đơn đạt điều kiện. Ứng viên không cần một danh sách những đơn mình
    trượt; nhân viên thì cần, và bản đầy đủ vẫn nằm trong nhật ký.
    """
    eligible = [item for item in log.get("items", []) if item.get("eligible")][:limit]
    return {
        "log_code": log["code"],
        "profile_code": log["profile_code"],
        "profile_version": log["profile_version"],
        "as_of": log["as_of"],
        "total_considered": log["total_considered"],
        "eligible_count": log["eligible_count"],
        "missing_info": log.get("missing_info", []),
        "matches": [public_item(item) for item in eligible],
        "disclaimer": (
            "Mức độ phù hợp tính trên giấy tờ, không phải cam kết trúng tuyển. "
            "Nhân viên tư vấn sẽ xác nhận lại trước khi nộp hồ sơ."
        ),
    }


def public_item(item: dict[str, Any]) -> dict[str, Any]:
    """Một đơn trong kết quả, kèm khối lý do và câu giải thích sinh bằng mã."""
    match_item = _rebuild(item)
    return {
        **item,
        "explanation_text": explain.render_template_text(match_item),
        "explanation_block": explain.render_block(match_item),
    }


def _rebuild(item: dict[str, Any]) -> engine.MatchItem:
    """Dựng lại đối tượng từ bản ghi đã lưu, để in ra đúng khối lý do cũ.

    Nhật ký lưu dạng từ điển chứ không lưu đối tượng, nên phải dựng lại. Nhờ vậy
    khối lý do hiển thị hôm nay đúng bằng khối đã sinh ra lúc đối chiếu, kể cả khi
    đơn hàng đã thay đổi từ đó tới giờ.
    """
    hard_rows = tuple(
        engine.CriterionRow(
            key=row["key"], label=row["label"],
            requirement_text=row["requirement_text"], candidate_text=row["candidate_text"],
            result=row["result"], missing_field=row.get("missing_field"), kind="cung",
        )
        for row in item.get("hard_rows", [])
    )
    soft_rows = tuple(
        engine.SoftRow(
            key=row["key"], label=row["label"],
            requirement_text=row["requirement_text"], candidate_text=row["candidate_text"],
            outcome=row["outcome"], points=row["points"], max_points=row["max_points"],
            missing_field=row.get("missing_field"), kind="mem",
        )
        for row in item.get("soft_rows", [])
    )
    return engine.MatchItem(
        code=item["code"], title=item["title"], employer_name=item["employer_name"],
        prefecture=item["prefecture"], region_group=item.get("region_group"),
        employer_type=item["employer_type"], program=item["program"],
        deadline=item["deadline"], eligible=item["eligible"], score=item["score"],
        rank=item.get("rank"), hard_rows=hard_rows, soft_rows=soft_rows,
        gaps=tuple(item.get("gaps", [])), missing_info=tuple(item.get("missing_info", [])),
        labels=item.get("labels", {}),
    )
