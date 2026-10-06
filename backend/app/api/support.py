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
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.auth.journey_security import require_journey_session
from app.auth.security import get_current_user
from app.consultation import khoi_doi_chieu, lien_he
from app.core.codes import PREFIX_SUPPORT, new_code
from app.core.phone import normalize_vietnamese_phone
from app.core.rate_limit import client_ip, rate_limiter
from app.core.session_id import SESSION_PATTERN
from app.db import advisor_turns
from app.db import support_requests as store
from app.db.database import create_notification, list_appointments_for_session
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

    # Khung giờ khách muốn gặp. Chỉ có nghĩa với `kind="gap_mat"`.
    #
    # Trước đây khách bấm "Xin gặp mặt" rồi nhân viên phải **gọi điện hỏi lại giờ
    # nào tiện** — trong khi khách vừa ngồi trước màn hình và sẵn sàng chọn. Và
    # màn hình lịch hẹn luôn trống với ai chỉ đi theo hành trình mới.
    #
    # Vẫn **không bắt buộc**: khách chưa biết lịch mình thì cứ gửi yêu cầu trống,
    # nhân viên hẹn lại. Bắt chọn giờ mới được xin gặp là dựng một cửa ở chỗ
    # không cần cửa.
    appointment_date: str | None = Field(default=None, max_length=10)
    appointment_time: str | None = Field(default=None, max_length=5)
    meeting_kind: Literal["truc_tiep", "truc_tuyen"] | None = None

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

    @field_validator("appointment_date")
    @classmethod
    def _ngay(cls, value: str | None) -> str | None:
        """Kiểm ngay ở tầng thân yêu cầu, để khách nhận câu nói rõ phải sửa gì.

        Kiểm sâu hơn trong luồng thì lỗi giờ sai sẽ rơi vào nhánh "không tạo
        được lịch, nuốt lỗi" — yêu cầu vẫn vào hàng đợi nhưng khách không biết
        giờ mình chọn đã bị bỏ, và vẫn tưởng mình có hẹn.
        """
        if value in (None, ""):
            return None
        from app.consultation import lich_hen

        return lich_hen.kiem_ngay(value)

    @field_validator("appointment_time")
    @classmethod
    def _gio(cls, value: str | None) -> str | None:
        if value in (None, ""):
            return None
        from app.consultation import lich_hen

        return lich_hen.kiem_gio(value)

    @model_validator(mode="after")
    def _ngay_va_gio_di_cung_nhau(self) -> "SupportRequestBody":
        """Có ngày mà không giờ là một cái hẹn không ai biết đến lúc nào.

        Thà từ chối và hỏi lại, hơn là tạo yêu cầu kèm một nửa thông tin rồi để
        nhân viên đoán.
        """
        if bool(self.appointment_date) != bool(self.appointment_time):
            raise ValueError(
                "Bạn chọn cả ngày và giờ giúp mình nhé, hoặc để trống cả hai và "
                "nhân viên sẽ hẹn lại."
            )
        return self


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
            "advice_block": await _khoi_doi_chieu(session_id, payload.job_order_code or ""),
            # Bản tóm tắt bàn giao: toàn bộ hành trình, không chỉ một đơn.
            #
            # `advice_block` ngay trên trả lời câu "khách vướng gì ở ĐƠN NÀY".
            # Bản này trả lời câu rộng hơn và là câu nhân viên thật sự cần trước
            # khi bấm số: khách là ai, đã xác nhận những gì, máy đọc được gì mà
            # chưa ai kiểm, đã hỏi những câu nào, câu nào trợ lý không trả lời
            # được, và việc nên làm tiếp.
            #
            # Dựng bằng mã, mô hình không tham gia: nhân viên sẽ đọc từng dòng
            # này ra miệng cho ứng viên nghe. Xem `app/agent/ban_giao.py`.
            "ban_giao": await _ban_giao(session_id, payload.message.strip()),
        }
    )

    # Lịch hẹn: tạo SAU khi yêu cầu đã vào hàng đợi, và không được làm gãy nó.
    #
    # Thứ tự có chủ ý. Yêu cầu hỗ trợ là thứ bảo đảm **có người gọi lại**; lịch
    # hẹn chỉ làm cuộc gọi đó đúng giờ hơn. Tạo lịch trước rồi yêu cầu lỗi thì
    # có một cái hẹn mà không ai biết để đến.
    ma_lich = await _tao_lich_hen(session_id, payload, document["code"])
    if ma_lich:
        document["appointment_code"] = ma_lich
        await _gan_lich_vao_yeu_cau(
            document["code"], ma_lich, session_id, payload.message.strip()
        )

    # Thông báo cho nhân viên nằm NGOÀI mọi nhánh trên.
    #
    # Trước 06/10 nó nằm sau lời gọi `gan_lich_hen` không có chốt chặn, nên một
    # lỗi database ở bước gắn liên kết kéo theo: lời gọi văng lỗi, nhân viên
    # không nhận thông báo, và khách thấy màn hình báo gửi thất bại trong khi
    # yêu cầu **và** lịch hẹn đều đã được tạo. Họ bấm lại, và lần bấm thứ hai bị
    # index duy nhất chặn — đúng về dữ liệu, nhưng khách vẫn không biết mình đã
    # gửi được hay chưa.
    await _bao_nhan_vien(document, payload.kind)
    return _da_nhan(document) | ({"appointment_code": ma_lich} if ma_lich else {})



async def _khoi_doi_chieu(session_id: str, job_order_code: str) -> str | None:
    """Khối kết quả đối chiếu đính kèm yêu cầu. Trả `None` khi không dựng được.

    **Không bao giờ làm gãy lời gọi của khách** — cùng lý do với `_ban_giao`. Bước
    này chạy TRƯỚC khi yêu cầu được tạo, nên một lỗi ở đây trước 06/10 nghĩa là
    yêu cầu không bao giờ vào hàng đợi: khách thấy "gửi thất bại", bấm lại, và có
    thể lại thất bại đúng chỗ ấy. Thiếu khối này thì nhân viên vẫn có bản bàn giao
    và số điện thoại; mất yêu cầu thì không ai gọi cả.
    """
    try:
        return await khoi_doi_chieu.dung_tu_nhat_ky(session_id, job_order_code)
    except Exception:  # noqa: BLE001 — xem docstring
        logger.warning(
            "Không dựng được khối đối chiếu cho phiên %s", session_id, exc_info=True
        )
        return None

async def _gan_lich_vao_yeu_cau(
    support_code: str, ma_lich: str, session_id: str, loi_nhan: str
) -> None:
    """Gắn mã lịch vào yêu cầu, và dựng lại bản bàn giao đã thấy lịch.

    **Không bao giờ ném lỗi ra ngoài.** Đến bước này thì hai thứ quan trọng đã
    nằm trong database: yêu cầu hỗ trợ (bảo đảm có người gọi lại) và lịch hẹn
    (bảo đảm cuộc gọi đúng giờ). Việc còn lại chỉ là một trường tiện tra cứu.

    ## Vì sao mất trường này không mất liên kết

    Liên kết được ghi **hai chiều, ở hai bản ghi khác nhau**: bản ghi lịch mang
    `support_code` ngay từ lúc tạo (`lich_hen.dung_ban_ghi`), còn yêu cầu mang
    `appointment_code` do bước này ghi. Bước này hỏng thì chiều thứ nhất vẫn
    nguyên, nên `store.lay_lich_hen_lien_quan()` lần ngược được từ phía lịch và
    **tự gắn lại** khi nhân viên mở yêu cầu.

    Nói cách khác: đây là trường **phi chuẩn hóa để tra nhanh**, không phải nguồn
    sự thật. Nguồn sự thật là `support_code` trên bản ghi lịch.

    ## Bản bàn giao thì chịu thiếu một khối

    Khối "KHÁCH ĐÃ CHỌN KHUNG GIỜ" sẽ rỗng cho tới khi có người mở yêu cầu lên
    (lúc ấy nó được dựng lại). Nhân viên vẫn thấy giờ hẹn ở màn hình lịch hẹn và
    ở chính dòng lịch trả về kèm yêu cầu.
    """
    try:
        await store.gan_lich_hen(
            support_code, ma_lich, ban_giao=await _ban_giao(session_id, loi_nhan)
        )
    except Exception:  # noqa: BLE001 — xem docstring
        logger.warning(
            "Yêu cầu %s: không gắn được lịch %s vào bản ghi. Liên kết vẫn còn ở "
            "phía lịch hẹn (support_code=%s) và sẽ được gắn lại khi nhân viên mở "
            "yêu cầu này.",
            support_code,
            ma_lich,
            support_code,
            exc_info=True,
        )


async def _tao_lich_hen(
    session_id: str, payload: "SupportRequestBody", support_code: str
) -> str | None:
    """Tạo lịch hẹn nếu khách đã chọn khung giờ. Trả mã lịch, hoặc `None`.

    Chỉ áp với `kind="gap_mat"`: hai loại kia là nhắn tin và hỏi về việc học,
    không cần ai có mặt vào một giờ cụ thể.

    **Không ném lỗi ra ngoài.** Giờ đã được kiểm ở tầng thân yêu cầu, nên đến đây
    chỉ còn những sự cố ngoài tầm khách — trùng lịch, database trục trặc. Để lời
    gọi thất bại vì chúng là chặn mất cả yêu cầu hỗ trợ, trong khi nhân viên vẫn
    gọi được nếu không có lịch.
    """
    if payload.kind != store.KIND_GAP_MAT:
        return None
    if not (payload.appointment_date and payload.appointment_time):
        return None

    from pymongo.errors import DuplicateKeyError

    from app.consultation import lich_hen
    from app.db.database import create_appointment

    try:
        ban_ghi = lich_hen.dung_ban_ghi(
            session_id=session_id,
            full_name=payload.full_name,
            phone=payload.phone,
            ngay=payload.appointment_date,
            gio=payload.appointment_time,
            job_order_code=payload.job_order_code,
            support_code=support_code,
            hinh_thuc=payload.meeting_kind or "truc_tuyen",
        )
        await create_appointment(ban_ghi)
        return ban_ghi["appointment_code"]
    except DuplicateKeyError:
        # Đã có lịch đúng số điện thoại, đúng ngày, đúng giờ. Không phải lỗi:
        # khách bấm hai lần, hoặc vừa hẹn qua khung chat. Index duy nhất trên
        # `booking_key` là chốt chặn thật, và nó vừa làm đúng việc.
        #
        # Nhưng phải **trả lại mã của lịch đã có**, không trả `None`.
        #
        # Bản trước trả `None`, và đường đi tệ nhất là thế này: lần bấm đầu tạo
        # được lịch nhưng lời gọi lỗi ở bước sau, khách bấm lại, lịch cũ chặn lịch
        # mới, máy chủ trả về không kèm mã lịch — và màn hình hiện dòng vàng
        # "khung giờ bạn chọn chưa thành lịch hẹn". Lịch thì có thật; chỉ có
        # khách là bị nói điều ngược lại.
        #
        # `booking_key` là số điện thoại + ngày + giờ, tức nó nhận diện **một
        # người ở một khung giờ**. Lịch khớp khóa ấy là lịch của chính người này,
        # dù họ hẹn qua hành trình tư vấn hay qua khung chat.
        da_co = await _lich_theo_khoa(ban_ghi["booking_key"])
        logger.info(
            "Yêu cầu %s: đã có lịch %s cùng số và cùng giờ, dùng lại thay vì tạo thêm.",
            support_code,
            (da_co or {}).get("appointment_code"),
        )
        return (da_co or {}).get("appointment_code")
    except Exception:  # noqa: BLE001 — xem docstring
        logger.warning(
            "Không tạo được lịch hẹn cho yêu cầu %s", support_code, exc_info=True
        )
        return None


async def _lich_theo_khoa(booking_key: str) -> dict[str, Any] | None:
    """Lịch hẹn đã có theo khóa chống trùng. Không ném lỗi."""
    try:
        from app.db.common import get_db

        return await get_db().consultation_appointments.find_one(
            {"booking_key": booking_key}, {"_id": 0, "appointment_code": 1}
        )
    except Exception:  # noqa: BLE001
        logger.warning("Không tra được lịch theo khóa chống trùng", exc_info=True)
        return None


async def _ban_giao(session_id: str, loi_nhan: str) -> str | None:
    """Bản tóm tắt bàn giao. Trả `None` khi không dựng được.

    **Không bao giờ làm gãy lời gọi của khách.** Khách vừa bấm "xin gặp nhân
    viên" sau khi đọc một kết quả nói họ chưa đủ điều kiện — để lời gọi ấy trả
    lỗi vì phần tóm tắt trục trặc là chặn đúng người đang cần giúp nhất.

    Thiếu bản tóm tắt thì nhân viên vẫn có `advice_block` và vẫn có số điện
    thoại; họ chỉ phải hỏi thêm vài câu. Mất yêu cầu thì không ai gọi cả.
    """
    try:
        from app.agent import ban_giao as builder
        from app.api.agent import _nap

        profile, trang_thai, log = await _nap(session_id)
        return builder.dung(
            profile=profile,
            trang_thai=trang_thai,
            log=log,
            # MỌI lượt, cả cấp hồ sơ lẫn từng đơn.
            #
            # `list_turns(session_id, None)` chỉ lấy phạm vi hồ sơ, nên khách hỏi
            # năm câu trong phòng tư vấn đơn DH-0001 rồi bấm "xin gặp nhân viên"
            # thì nhân viên nhận một phiếu **không có câu nào khách đã hỏi**.
            # Dữ liệu vẫn nằm trong database, chỉ là không ai mang nó sang.
            luot_hoi=await advisor_turns.list_all_turns(session_id),
            # Lịch hẹn: thứ duy nhất trong bản bàn giao có mốc thời gian,
            # nên nó quyết định thứ tự việc trong ngày của nhân viên.
            lich_hen=await list_appointments_for_session(session_id),
            loi_nhan=loi_nhan,
        )
    except Exception:  # noqa: BLE001 — xem docstring
        logger.warning(
            "Không dựng được bản bàn giao cho phiên %s", session_id, exc_info=True
        )
        return None


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


@router.get("/{code}")
async def chi_tiet(
    code: Annotated[str, Path(pattern=CODE_PATTERN)],
    current_user=Depends(get_current_user),
) -> dict[str, Any]:
    """Một yêu cầu, kèm lịch hẹn nếu có.

    Lịch hẹn tra **từ phía lịch** (`support_code`) chứ không tin trường
    `appointment_code` trên yêu cầu, và gắn lại trường ấy nếu nó thiếu — xem
    `store.lay_lich_hen_lien_quan`. Nhờ vậy một lỗi database ở bước gắn liên kết
    lúc tạo không làm nhân viên mất giờ hẹn của khách.
    """
    document = await store.get_request(code)
    if document is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu này.")
    lich = await _dong_bo_lich(document)
    return {"request": document, "appointment": lich}


async def _dong_bo_lich(document: dict[str, Any]) -> dict[str, Any] | None:
    """Tra lịch hẹn của yêu cầu, và sửa **cả liên kết lẫn bản bàn giao** nếu lệch.

    Gọi ở **mọi** đường nhân viên đọc một yêu cầu: mở chi tiết, nhận xử lý.
    Hai đường từng sửa theo hai cách khác nhau — một đường sửa liên kết mà không
    dựng lại bàn giao — và thứ tự bấm của nhân viên quyết định họ thấy giờ hẹn
    hay không. Một hàm cho mọi đường thì không còn thứ tự nào sai.

    Tín hiệu lệch là `store.can_dung_lai_ban_giao`: bản bàn giao đã lưu được
    dựng với lịch nào. Không phải `appointment_code` có trống hay không.

    Không ném lỗi. Thiếu một khối trong bản bàn giao thì nhân viên vẫn có mã
    lịch và số điện thoại; còn lời gọi gãy thì họ không mở được yêu cầu.
    Sửa hỏng thì `ban_giao_lich` vẫn lệch, nên lần mở sau tự thử lại.
    """
    try:
        lich = await store.lay_lich_hen_lien_quan(document["code"])
    except Exception:  # noqa: BLE001
        logger.warning("Không tra được lịch hẹn của %s", document.get("code"), exc_info=True)
        return None
    if lich is None:
        return None

    ma = lich.get("appointment_code")
    document["appointment_code"] = ma
    if not store.can_dung_lai_ban_giao(document, lich):
        return lich

    try:
        moi = await _ban_giao(
            document.get("session_id") or "", document.get("message") or ""
        )
        # `moi` là None khi dựng hỏng: vẫn gắn liên kết, nhưng KHÔNG ghi
        # `ban_giao_lich`, để lần mở sau còn biết mà dựng lại.
        await store.gan_lich_hen(document["code"], ma, ban_giao=moi)
        if moi:
            document["ban_giao"] = moi
            document["ban_giao_lich"] = ma
            logger.info("Đã dựng lại bản bàn giao cho %s với lịch %s.", document["code"], ma)
    except Exception:  # noqa: BLE001 — xem docstring
        logger.warning(
            "Không đồng bộ được lịch %s vào yêu cầu %s", ma, document.get("code"), exc_info=True
        )
    return lich


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
    # Nhận xử lý là lúc nhân viên thật sự đọc yêu cầu. Đi qua đúng một hàm với
    # đường mở chi tiết — xem `_dong_bo_lich`. `_dong_bo_lich` không ném lỗi,
    # nên việc nhận không bao giờ gãy vì bước này.
    await _dong_bo_lich(document)
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
