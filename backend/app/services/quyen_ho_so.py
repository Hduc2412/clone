"""Ai được làm việc với một hồ sơ ứng viên — **một** quy tắc cho mọi đường.

## Quy tắc

Một nhân viên thường làm việc được với hồ sơ ứng viên khi:

1. được phân công **trực tiếp** hồ sơ ấy (`candidate_profiles.assigned_to`), hoặc
2. đang phụ trách một hồ sơ **đăng ký còn mở** của ứng viên ấy.

Quản lý và quản trị viên thì luôn được. Mọi thứ thuộc về hồ sơ — CV gốc, nhật ký
giới thiệu — dùng **đúng quy tắc này, trên hồ sơ hiện tại**.

## Lỗi thứ nhất, 06/10: người vừa nhận khách bị 403

Nhận hồ sơ đăng ký từ hàng đợi chỉ gán hồ sơ *đăng ký*, không gán hồ sơ *ứng
viên*. Nên người vừa nhận khách không xem được hồ sơ, CV, nhật ký. Bộ đo cũ chạy
bằng admin nên không thấy. Sửa bằng điều 2 ở trên — tính lúc đọc, để chuyển
giao, trả về hàng đợi, đóng hồ sơ thì quyền tự đi theo.

## Lỗi thứ hai, cũng 06/10: nhật ký dùng ảnh chụp để cấp quyền

`recommendation_logs.assigned_to` là **ảnh chụp** người phụ trách hồ sơ tại lúc
đối chiếu (`matching_service`). Bản sửa thứ nhất vẫn dùng nó làm đường **cho
phép** đầu tiên — dù chính docstring của bản ấy ghi rõ đó là ảnh chụp. Chủ đồ án
tái hiện: hồ sơ chuyển từ A sang B thì

- A **không còn** xem được hồ sơ, nhưng **vẫn** đọc được nhật ký cũ;
- B xem được hồ sơ, nhưng nhật ký cũ trả 403.

Nghĩa là quyền đọc nhật ký bám người phụ trách của **quá khứ**. Nay nhật ký không
bao giờ dùng `assigned_to` của chính nó: `co_quyen_nhat_ky` tra hồ sơ hiện tại
rồi áp `co_quyen_ho_so`, và danh sách nhật ký lọc theo **mã hồ sơ** mình được
xem. Trường ảnh chụp vẫn còn trong bản ghi — nó là lịch sử đúng, chỉ không còn
là căn cứ cấp quyền.

## Điều 3, 08/10: người đang giữ yêu cầu hỗ trợ — CHỈ ĐỌC, và chỉ khi khách đồng ý

Nhân viên đang giữ một yêu cầu hỗ trợ (`dang_xu_ly`, `assigned_to` là mình) được **đọc**
hồ sơ và CV gắn với chính yêu cầu ấy — nối qua `session_id` của yêu cầu, không qua số
điện thoại — nếu khách đã tích "đồng ý bàn giao" lúc gửi (`dong_y_ban_giao`). Yêu cầu
cũ không có trường ấy thì coi như chưa đồng ý. Chuyển yêu cầu sang người khác thì
người cũ mất quyền ngay, vì quyền tính từ `assigned_to` hiện tại. Sửa hồ sơ thì vẫn
theo hai điều ở trên — giữ một yêu cầu hỗ trợ không biến ai thành người phụ trách hồ sơ.

## Phạm vi

Đúng những đường trước đây kiểm quyền theo hồ sơ ứng viên: xem và sửa hồ sơ,
danh sách và nội dung CV, nhật ký giới thiệu, chạy lại đối chiếu.
"""
from typing import Any

from app.db import candidate_profiles as profile_store
from app.db.database import list_recruitment_applications
from app.services.assignment import is_privileged

# Đủ lớn cho một nhân viên tư vấn: một người phụ trách vài chục hồ sơ đang mở là
# nhiều. Có trần để một lỗi dữ liệu không biến phép kiểm quyền thành một lần đọc
# cả bảng.
TRAN = 500


def _email(current_user: dict) -> str:
    return (current_user.get("email") or "").strip().lower()


async def ma_ho_so_qua_don(email: str) -> set[str]:
    """Mã hồ sơ ứng viên mà `email` đang phụ trách qua một hồ sơ đăng ký còn mở."""
    don = await list_recruitment_applications(assigned_to=email, active_only=True, limit=TRAN)
    return {d["profile_code"] for d in don if d.get("profile_code")}


async def ma_ho_so_truc_tiep(email: str) -> set[str]:
    """Mã hồ sơ ứng viên đang được phân công trực tiếp cho `email` — giá trị HIỆN TẠI."""
    ds = await profile_store.list_profiles({"assigned_to": email}, limit=TRAN)
    return {p["code"] for p in ds if p.get("code")}


async def phien_qua_ho_tro(email: str) -> set[str]:
    """Phiên của các yêu cầu hỗ trợ `email` ĐANG giữ mà khách đã đồng ý bàn giao (điều 3)."""
    from app.db import support_requests as ho_tro

    ds = await ho_tro.list_requests(status=ho_tro.STATUS_DANG_XU_LY, assigned_to=email, limit=TRAN)
    return {d["session_id"] for d in ds if d.get("dong_y_ban_giao") is True and d.get("session_id")}


async def co_quyen_ho_so(profile: dict[str, Any], current_user: dict, *, chi_doc: bool = False) -> bool:
    """Quy tắc gốc, trên chính hồ sơ ứng viên. Xét theo thứ tự rẻ trước.

    `chi_doc=True` cho các đường chỉ ĐỌC (xem hồ sơ, CV, nhật ký): mở thêm điều 3.
    """
    if is_privileged(current_user):
        return True
    email = _email(current_user)
    if profile.get("assigned_to") == email:
        return True
    ma = profile.get("code")
    if bool(ma) and ma in await ma_ho_so_qua_don(email):
        return True
    return chi_doc and bool(profile.get("session_id")) and profile["session_id"] in await phien_qua_ho_tro(email)


async def co_quyen_nhat_ky(log: dict[str, Any], current_user: dict) -> bool:
    """Quyền đọc một nhật ký giới thiệu = quyền với hồ sơ **hiện tại** của nó.

    Không đọc `log["assigned_to"]`. Xem phần "Lỗi thứ hai" ở đầu module.
    Nhật ký không gắn hồ sơ nào, hoặc hồ sơ đã bị xóa: chỉ quản lý đọc được.
    """
    if is_privileged(current_user):
        return True
    ma = log.get("profile_code")
    if not ma:
        return False
    profile = await profile_store.get_by_code(ma)
    if profile is None:
        return False
    return await co_quyen_ho_so(profile, current_user, chi_doc=True)


async def dieu_kien_ho_so(query: dict[str, Any], current_user: dict) -> dict[str, Any]:
    """Thu hẹp danh sách hồ sơ ứng viên về đúng phần người này được xem.

    Ở đây lọc `assigned_to` là đúng, vì đó là trường sở hữu HIỆN TẠI của chính
    hồ sơ — khác với ảnh chụp trên nhật ký. Nhân viên thường không dùng được bộ
    lọc `assigned_to=<người khác>` để xem phần của người khác.
    """
    if is_privileged(current_user):
        return query
    email = _email(current_user)
    hep = {k: v for k, v in query.items() if k != "assigned_to"}
    hoac: list[dict[str, Any]] = [{"assigned_to": email}]
    ma = sorted(await ma_ho_so_qua_don(email))
    if ma:
        hoac.append({"code": {"$in": ma}})
    phien = sorted(await phien_qua_ho_tro(email))
    if phien:
        hoac.append({"session_id": {"$in": phien}})
    return _ghep(hep, hoac)


async def dieu_kien_nhat_ky(query: dict[str, Any], current_user: dict) -> dict[str, Any]:
    """Thu hẹp danh sách nhật ký về những hồ sơ người này được xem **lúc này**.

    Lọc theo `profile_code`, không theo `assigned_to` của nhật ký: trường ấy là
    ảnh chụp, và lọc theo nó là cho người phụ trách cũ thấy mãi còn người phụ
    trách mới không thấy gì.
    """
    if is_privileged(current_user):
        return query
    email = _email(current_user)
    hep = {k: v for k, v in query.items() if k != "assigned_to"}
    ma = await ma_ho_so_truc_tiep(email) | await ma_ho_so_qua_don(email)
    phien = sorted(await phien_qua_ho_tro(email))
    if phien:
        ma |= {p["code"] for p in await profile_store.list_profiles({"session_id": {"$in": phien}}, limit=TRAN) if p.get("code")}
    dk = {"profile_code": {"$in": sorted(ma)}}
    if "profile_code" in hep:
        # Người gọi lọc một hồ sơ cụ thể: giữ điều kiện của họ VÀ của quyền.
        return {"$and": [hep, dk]}
    return {**hep, **dk}


def _ghep(hep: dict[str, Any], hoac: list[dict[str, Any]]) -> dict[str, Any]:
    if "$or" in hep:
        # Câu truy vấn gốc đã có `$or` của riêng nó: ghép bằng `$and` thay vì đè.
        return {"$and": [hep, {"$or": hoac}]}
    return {**hep, "$or": hoac}
