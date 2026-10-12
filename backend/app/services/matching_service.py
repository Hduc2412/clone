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


class DonKhongCo(Exception):
    """Mã đơn không có trong danh mục đang công khai."""


async def run_matching(
    profile: dict[str, Any],
    *,
    trigger: str,
    actor_email: str | None = None,
    as_of: date | None = None,
    force: bool = False,
    chi_don: str | None = None,
) -> tuple[dict[str, Any], bool]:
    """Chạy đối chiếu và ghi nhật ký. Trả về bản ghi và cờ cho biết có dùng lại không.

    `chi_don` giới hạn danh mục xuống **đúng một đơn**, cho luồng tư vấn theo đơn:
    khách đang xem một đơn cụ thể và hỏi "tôi có hợp đơn này không".

    Bộ đối chiếu không phải sửa gì — nó vốn nhận một danh sách, truyền vào một
    phần tử là xong. Nhật ký vẫn ghi như thường, nên mọi chốt chặn của luồng
    đăng ký (phải có trong nhật ký, phải đạt điều kiện, phải đúng phiên bản hồ
    sơ) vẫn áp dụng nguyên vẹn — luồng mới **không nới điều nào**.

    Bộ nhớ đệm không lẫn giữa hai luồng: khóa đệm gồm `orders_fingerprint`, mà
    vân tay của một đơn khác hẳn vân tay của cả danh mục.
    """
    reference_date = as_of or local_today()
    weights = load_weights()
    pool = await load_pool()
    if chi_don is not None:
        pool = [don for don in pool if don.get("code") == chi_don]
        if not pool:
            raise DonKhongCo(chi_don)
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
        # Nhật ký một đơn phải nhận ra được, để không ai lấy nó làm "lần đối chiếu
        # gần nhất" của cả danh mục — xem `recommendation_logs.latest_for_profile`.
        "chi_don": chi_don,
        "total_considered": payload["total_considered"],
        "eligible_count": payload["eligible_count"],
        "top_codes": [item.code for item in result.top(DEFAULT_TOP_N)],
        "missing_info": payload["missing_info"],
        "items": [_gon_lai(item) for item in payload["items"]],
        "trigger": trigger,
        "actor_email": actor_email,
    }
    return await recommendation_logs.create_log(document), False


async def dong_day_du(
    profile: dict[str, Any], row: dict[str, Any], *, as_of: date | None = None
) -> dict[str, Any]:
    """Dòng nhật ký của một đơn, kèm ĐỦ các tiêu chí bắt buộc để hiển thị.

    Nhật ký rút gọn đơn bị loại (`_gon_lai`): chỉ giữ dòng không đạt. Đủ cho việc
    đối chứng, thiếu cho bảng đối chiếu khách xem — bảng phải hiện cả tiêu chí đã
    đạt. Nên với dòng đã rút gọn, chấm lại đúng đơn ấy bằng engine — thuần, tất định,
    cùng hồ sơ và cùng ngày thì ra đúng các dòng đã chấm — và KHÔNG ghi nhật ký mới.
    Dòng chưa rút gọn trả nguyên.
    """
    if row.get("eligible") or not row.get("hard_rows_passed"):
        return row
    don = next((d for d in await load_pool() if d.get("code") == row.get("code")), None)
    if don is None:
        return row
    ngay = as_of or local_today()
    ket = engine.match_orders(
        [don], engine.build_facts(profile, ngay), weights=load_weights(), as_of=ngay
    ).as_dict()["items"]
    if not ket:
        return row
    day_du = ket[0]
    # Chỉ lấy phần dòng tiêu chí; kết luận giữ nguyên theo nhật ký.
    return {**row, "hard_rows": [_bo_nhan_suy_ra(d) for d in day_du["hard_rows"]]}


async def ca_danh_muc_cho_tu_van(
    profile: dict[str, Any], *, trigger: str
) -> dict[str, Any] | None:
    """Kết quả đối chiếu **cả danh mục** để trợ lý giới thiệu đơn khác — hoặc `None`.

    Trợ lý không được tự chọn đơn. Nó chỉ nói lại đơn mà bộ đối chiếu đã chấm, nên
    khi cần đơn khác thì chạy đúng `run_matching` như trang kết quả — có bộ đệm 10
    phút theo phiên bản hồ sơ và vân tay danh mục, nên hỏi nhiều câu liền không đối
    chiếu lại nhiều lần.

    Chỉ chạy với hồ sơ **đã xác nhận**, cùng quy tắc với trang kết quả
    (`/public/matches` trả 409 khi chưa xác nhận). Hồ sơ máy vừa đọc từ CV có thể đọc
    nhầm; giới thiệu cả danh mục từ chỗ đọc nhầm ấy là đẩy khách đi sai đường.
    """
    from app.db import candidate_profiles as profiles

    if profile.get("status") != profiles.STATUS_CONFIRMED:
        return None
    log, _ = await run_matching(profile, trigger=trigger)
    return log


def _gon_lai(item: dict[str, Any]) -> dict[str, Any]:
    """Rút gọn một đơn **bị loại** trước khi lưu vào nhật ký.

    ## Đo được gì

    Một bản nhật ký nặng 50 KB — bằng 140 tin nhắn chat — và chiếm 68% toàn bộ
    cơ sở dữ liệu dù chỉ có 26 bản ghi. Bóc ra: 49/50 KB là mảng `items`, trong
    đó **37 KB là 15 đơn bị loại**. Mỗi đơn mang đủ bảy dòng tiêu chí, mà với đơn
    đã trượt thì năm sáu dòng trong đó ghi "ĐẠT" — chúng không nói gì về lý do
    trượt, chỉ tốn chỗ.

    Con số này còn xấu đi theo quy mô: nó tỉ lệ thuận với số đơn trong danh mục.
    Mười tám đơn cho 50 KB; hai trăm đơn thì một lần đối chiếu là nửa megabyte.

    ## Giữ lại đúng thứ cần cho việc đối chứng

    Nhật ký tồn tại để trả lời hai câu: *bộ lọc có chạy không* và *vì sao đơn này
    trượt*. Nên đơn bị loại giữ lại những dòng **không đạt** cùng `gaps` và
    `missing_info`, thêm `hard_rows_passed` đếm số dòng đã đạt — đủ chứng minh
    cả bảy tiêu chí đều được xét. Phần bỏ đi là các dòng đạt, và `soft_rows` vốn
    luôn rỗng với đơn bị loại vì bộ đối chiếu không chấm điểm đơn đã trượt.

    Đơn **đạt** giữ nguyên không đụng tới: ứng viên xem được bảng lý do đầy đủ
    của chúng, và phiếu bàn giao dựng lại khối giải thích từ chính dữ liệu này.
    """
    gon = {
        **item,
        "hard_rows": [_bo_nhan_suy_ra(row) for row in item.get("hard_rows") or []],
        "soft_rows": [_bo_nhan_suy_ra(row) for row in item.get("soft_rows") or []],
    }
    if item.get("eligible"):
        return gon

    tat_ca = gon["hard_rows"]
    khong_dat = [row for row in tat_ca if row.get("result") != engine.DAT]
    gon["hard_rows"] = khong_dat
    gon["hard_rows_passed"] = len(tat_ca) - len(khong_dat)
    # `soft_rows` của đơn bị loại luôn rỗng; bỏ hẳn khóa cho gọn bản ghi.
    gon.pop("soft_rows", None)
    return gon


def _bo_nhan_suy_ra(row: dict[str, Any]) -> dict[str, Any]:
    """Bỏ nhãn hiển thị suy ra được, đừng lưu bản sao của nó.

    `result_label` chỉ là `RESULT_LABELS[result]`. Lưu nó vào từng dòng, của
    từng đơn, của từng lần đối chiếu là nhân bản cùng một chuỗi hàng nghìn lần:
    đo được 109 KB trên 26 bản nhật ký, tức 7% toàn bộ cơ sở dữ liệu.

    Không mất gì khi đọc: `CriterionRow.as_dict()` sinh lại nhãn từ `result`,
    nên API vẫn trả về đủ như cũ. Và làm vậy còn đúng hơn — sửa cách gọi tên một
    kết quả thì mọi bản ghi cũ hiển thị theo tên mới, thay vì đóng băng tên cũ
    trong dữ liệu.
    """
    return {khoa: gia_tri for khoa, gia_tri in row.items() if khoa != "result_label"}


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
        # Điểm có nghĩa để hiện hay chưa. Tính ở đây, một lần, thay vì để hai
        # màn hình tự suy từ `score` — xem `engine.xep_hang_duoc`.
        "score_ranked": engine.xep_hang_duoc(match_item.soft_rows),
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
        engine.SoftRow.tu_ban_ghi({**row, "kind": "mem"})
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
