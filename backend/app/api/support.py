"""Yêu cầu hỗ trợ: khách gửi, nhân viên trả lời trong giờ làm việc.

## Vì sao không làm chat thời gian thực

Khách thấy đúng một màn hình trò chuyện và gõ được bất cứ lúc nào — kể cả mười
một giờ đêm, giờ phần lớn người lao động rảnh để tìm hiểu. Khác biệt nằm ở chỗ
giao diện nói rõ **nhân viên trả lời trong giờ làm việc**, thay vì hứa một thứ
không giữ được rồi để người ta ngồi đợi trước màn hình im lặng.

Chat thời gian thực đòi có người trực liên tục — đó là bài toán vận hành, không
phải bài toán kỹ thuật, và `docs/design/13 §1.2` đã xếp nó ngoài phạm vi. Cách
này giữ đúng phạm vi mà vẫn cho khách hỏi lúc nửa đêm: trợ lý trả lời ngay,
nhân viên trả lời sáng hôm sau.

## Không nới chốt chặn đăng ký

Người chưa đủ điều kiện đi qua cửa này, **không** đi qua cửa đăng ký. Chốt chặn ở
`registration_service` giữ nguyên: đơn phải nằm trong nhật ký giới thiệu và phải
đạt điều kiện. Nhờ vậy hàng đợi tuyển dụng vẫn chỉ chứa hồ sơ dùng được.

## Không hỏi và không lưu chuyện bệnh tật

Khách thấy mình có thể không đủ điều kiện sức khỏe thì gửi một yêu cầu hỗ trợ —
và yêu cầu đó **không ghi bệnh gì**. Hệ thống chỉ biết "người này muốn được tư
vấn", không biết vì sao.
"""
import logging
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.auth.journey_security import require_journey_session
from app.auth.security import get_current_user
from app.consultation import khoi_doi_chieu, lien_he
from app.core.codes import PREFIX_SUPPORT, new_code
from app.core.phone import normalize_vietnamese_phone
from app.core.rate_limit import client_ip, rate_limiter
from app.core.session_id import SESSION_PATTERN
from app.db import support_requests as store
from app.db.database import create_notification
from app.services.assignment import is_privileged
from app.services.audit_service import audit_action


logger = logging.getLogger(__name__)


public_router = APIRouter(
    prefix="/tu-van/v1",
    tags=["Yêu cầu hỗ trợ (công khai)"],
    dependencies=[Depends(require_journey_session)],
)
router = APIRouter(
    prefix="/ho-tro",
    tags=["Yêu cầu hỗ trợ"],
    dependencies=[Depends(get_current_user)],
)

# Khung giờ nói với khách khi mời họ liên hệ. Cố ý gọn hơn giờ làm việc chính
# thức (08:00–11:30 và 13:30–17:00): khoảng nghỉ trưa chỉ cần chi tiết ở phần đặt
# lịch hẹn, nơi hệ thống thật sự chặn khung giờ đó. Còn khi chỉ mời người ta nhắn
# tin hay gọi điện thì bắt họ nhớ hai khoảng giờ rời nhau là đặt một rào cản
# không cần thiết.
# Một nguồn duy nhất cho giờ liên hệ. Trước 29/09 hằng số này chỉ có ở đây, nên
# bot tư vấn không biết giờ làm việc dù công ty có khai — xem
# `app/consultation/lien_he.py`.
GIO_LIEN_HE = lien_he.GIO_LIEN_HE

CODE_PATTERN = r"^HT-[0-9A-F]{6}$"


class SupportRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["nhan_tin", "hoc_tap", "gap_mat"]
    # Lời nhắn KHÔNG bắt buộc.
    #
    # Khách vừa đọc một khối kết quả nói rõ họ vướng ở đâu, rồi bấm "xin gặp nhân
    # viên". Bắt họ gõ lại bằng lời của mình là bắt diễn đạt lại một thứ hệ thống
    # đã biết — và với người đang thất vọng vì vừa bị báo chưa đủ điều kiện thì
    # đó là một bậc thềm đủ cao để họ bỏ đi. Để trống thì máy chủ tự điền một câu
    # theo loại yêu cầu, xem `_LOI_NHAN_MAC_DINH`.
    message: str = Field(default="", max_length=2000)
    full_name: str = Field(min_length=2, max_length=100)
    phone: str = Field(min_length=6, max_length=20)
    job_order_code: str | None = Field(default=None, max_length=20)

    # KHÔNG có trường `advice_block`, và đó là chủ ý.
    #
    # Bản trước nhận khối kết quả đối chiếu từ thân yêu cầu rồi lưu nguyên văn —
    # trình duyệt gửi gì máy chủ tin nấy, nên khách sửa được trước khi gửi và
    # nhân viên đọc một bản "kết quả đối chiếu" không do bộ đối chiếu sinh ra.
    # Cùng loại sai với việc tin mã phiên trình duyệt tự đặt. Nay máy chủ tự dựng
    # lại từ nhật ký giới thiệu, xem `consultation/khoi_doi_chieu.py`.

    @field_validator("phone", mode="before")
    @classmethod
    def _phone(cls, value: object) -> str:
        return normalize_vietnamese_phone(str(value or ""))


class ReplyBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reply: str = Field(min_length=1, max_length=4000)


@public_router.post("/{session_id}/ho-tro", status_code=201)
async def gui_yeu_cau(
    session_id: Annotated[str, Path(pattern=SESSION_PATTERN)],
    payload: SupportRequestBody,
    http_request: Request,
) -> dict[str, Any]:
    """Khách gửi một yêu cầu cần người xử lý."""
    # Chặt hơn các đường đọc: đây là đường ghi và nó tạo việc cho nhân viên thật.
    rate_limiter.check(f"ho-tro:{client_ip(http_request)}", limit=5, window_seconds=600)

    # Bấm hai lần không tạo hai việc.
    #
    # Nút gửi nằm ở cuối một màn hình dài, mạng di động thì chậm, và không có gì
    # nhúc nhích trong một giây — người ta bấm lại. Mỗi lần bấm một dòng thì hai
    # nhân viên nhận hai yêu cầu của cùng một người rồi gọi cho họ hai lần.
    #
    # Chốt chặn thật nằm ở **index duy nhất** trong `store.create_request`, không
    # nằm ở đây. Lần tra trước đó chỉ để tránh sinh mã và tránh dựng lại khối đối
    # chiếu một cách vô ích; hai lần bấm sát nhau thì cả hai đều thấy "chưa có", và
    # chỉ index mới chặn được. Bản rà soát 30/09 đã tái hiện đúng khoảng hở ấy.
    document, _moi = await store.create_request(
        {
            "code": new_code(PREFIX_SUPPORT),
            "kind": payload.kind,
            "session_id": session_id,
            "full_name": payload.full_name.strip(),
            "phone": payload.phone,
            "message": payload.message.strip() or _LOI_NHAN_MAC_DINH[payload.kind],
            "job_order_code": payload.job_order_code,
            # Máy chủ tự dựng, không nhận từ trình duyệt.
            "advice_block": await khoi_doi_chieu.dung_tu_nhat_ky(
                session_id, payload.job_order_code or ""
            ),
        }
    )

    await _bao_nhan_vien(document, payload.kind)
    return _da_nhan(document)


async def _bao_nhan_vien(document: dict[str, Any], kind: str) -> None:
    """Ghi thông báo cho nhân viên. **Không bao giờ làm gãy lời gọi của khách.**

    Yêu cầu đã nằm trong bảng rồi. Ném lỗi ra ngoài lúc này là trả 500 cho một
    thao tác đã thành công — khách tưởng mình chưa gửi được và bấm lại, rồi nhận
    201, rồi vẫn không ai liên hệ vì thông báo chưa từng được ghi.
    Bản rà soát 30/09 dựng đúng cảnh đó.

    Đã báo rồi thì không báo lại: `notified_at` là mốc phân biệt "đã báo" với "báo
    hỏng", và nhờ nó lần gửi lại **báo bù** thay vì im lặng bỏ qua.
    """
    if document.get("notified_at"):
        return
    try:
        await create_notification(
            notification_type="new_support_request",
            title=_TIEU_DE_THONG_BAO[kind],
            reference_type="support_request",
            reference_code=document["code"],
            detail={"customer_name": document["full_name"], "kind": kind},
        )
    except Exception:
        # Ghi log, không ném. Mốc `notified_at` vẫn `None`, nên lần khách gửi lại
        # sẽ thử lại — và hàng đợi quản trị đọc được cờ ấy để biết việc nào chưa
        # có thông báo.
        logger.warning(
            "Không ghi được thông báo cho yêu cầu hỗ trợ %s. Yêu cầu vẫn đã lưu; "
            "lần gửi lại sẽ thử báo lại.",
            document["code"],
            exc_info=True,
        )
        return
    await store.danh_dau_da_thong_bao(document["code"])


def _da_nhan(document: dict[str, Any]) -> dict[str, Any]:
    """Câu trả lời cho khách. Giống hệt nhau dù là yêu cầu mới hay yêu cầu đã có.

    Nói "bạn đã gửi rồi" chỉ làm người ta lo là lần này không tính. Thứ họ cần
    biết là yêu cầu đã tới nơi và bao giờ có người trả lời.
    """
    return {
        "code": document["code"],
        "kind": document["kind"],
        "message": (
            "Đã gửi tới nhân viên tư vấn. Xin vui lòng liên hệ với nhân viên "
            f"trong khoảng thời gian từ {GIO_LIEN_HE}, thứ Hai đến thứ Bảy."
        ),
    }


@public_router.get("/{session_id}/ho-tro")
async def yeu_cau_cua_toi(
    session_id: Annotated[str, Path(pattern=SESSION_PATTERN)],
) -> dict[str, Any]:
    """Khách xem lại mình đã hỏi gì và nhân viên đã trả lời chưa."""
    items = await store.list_for_session(session_id)
    return {"items": [_ban_cho_khach(item) for item in items]}


# Lời nhắn máy chủ tự điền khi khách để trống. Viết ở ngôi của khách, vì nhân
# viên đọc hàng đợi sẽ đọc nó như lời khách nói.
_LOI_NHAN_MAC_DINH = {
    store.KIND_NHAN_TIN: "Khách để lại yêu cầu, chưa ghi nội dung cụ thể.",
    store.KIND_HOC_TAP: "Khách muốn được tư vấn về việc học tiếng Nhật.",
    store.KIND_GAP_MAT: "Khách muốn gặp nhân viên tư vấn để trao đổi thêm.",
}

_TIEU_DE_THONG_BAO = {
    store.KIND_NHAN_TIN: "Khách để lại tin nhắn",
    store.KIND_HOC_TAP: "Khách muốn tư vấn về việc học",
    store.KIND_GAP_MAT: "Khách xin gặp mặt",
}

# Trường khách được xem lại. Danh sách cho phép, không phải danh sách loại trừ:
# thêm một trường nội bộ vào bản ghi sau này sẽ không vô tình lọt ra.
_KHACH_XEM = ("code", "kind", "status", "message", "reply", "created_at", "handled_at")


def _ban_cho_khach(item: dict[str, Any]) -> dict[str, Any]:
    return {key: item.get(key) for key in _KHACH_XEM}


# --- Cửa nội bộ ---


@router.get("")
async def hang_doi(
    status: str | None = Query(default=store.STATUS_CHO, max_length=20),
    kind: str | None = Query(default=None, max_length=20),
    limit: int = Query(default=100, ge=1, le=300),
    current_user=Depends(get_current_user),
) -> dict[str, Any]:
    """Hàng đợi hỗ trợ. Không lọc theo người phụ trách — ai rảnh thì nhận.

    Cố ý giống `/registrations/queue`: hàng đợi là chỗ việc chưa có chủ, nên lọc
    theo người phụ trách ở đây sẽ biến nó thành một danh sách rỗng với người mới.
    """
    items = await store.list_requests(status=status, kind=kind, limit=limit)
    return {"items": items, "count": len(items)}


@router.get("/cua-toi")
async def cua_toi(current_user=Depends(get_current_user)) -> dict[str, Any]:
    items = await store.list_requests(
        status=None, assigned_to=current_user["email"], limit=200
    )
    return {"items": items, "count": len(items)}


@router.post("/{code}/nhan")
async def nhan_xu_ly(
    code: Annotated[str, Path(pattern=CODE_PATTERN)],
    http_request: Request,
    current_user=Depends(get_current_user),
) -> dict[str, Any]:
    document = await store.claim(code, email=current_user["email"])
    if document is None:
        # Phân biệt "không có" với "người khác vừa nhận" — hai chuyện dẫn tới hai
        # hành động khác nhau cho người đang bấm.
        hien_co = await store.get_request(code)
        if hien_co is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu này.")
        raise HTTPException(
            status_code=409,
            detail=f"Yêu cầu này vừa được {hien_co.get('assigned_to') or 'người khác'} nhận.",
        )
    await audit_action(
        http_request,
        "support.claimed",
        actor=current_user,
        target_type="support_request",
        target_id=code,
    )
    return document


@router.post("/{code}/tra-loi")
async def tra_loi(
    code: Annotated[str, Path(pattern=CODE_PATTERN)],
    payload: ReplyBody,
    http_request: Request,
    current_user=Depends(get_current_user),
) -> dict[str, Any]:
    hien_co = await store.get_request(code)
    if hien_co is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu này.")
    # Người đang giữ mới được trả lời; quản lý thì được, để việc không kẹt khi
    # người nhận nghỉ.
    giu = hien_co.get("assigned_to")
    if giu and giu != current_user["email"] and not is_privileged(current_user):
        raise HTTPException(
            status_code=403,
            detail=f"Yêu cầu này do {giu} đang xử lý.",
        )

    document = await store.close_request(
        code, email=current_user["email"], reply=payload.reply.strip()
    )
    await audit_action(
        http_request,
        "support.replied",
        actor=current_user,
        target_type="support_request",
        target_id=code,
    )
    return document
