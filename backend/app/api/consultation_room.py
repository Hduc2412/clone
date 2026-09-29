"""Phòng tư vấn cho một đơn tuyển dụng cụ thể.

## Khác gì với `/public/matches`

`/public/matches/{session}` trả lời câu *"tôi hợp đơn nào"* — đối chiếu hồ sơ với
cả danh mục rồi xếp hạng. Đường này trả lời câu hẹp hơn và thường là câu người ta
thật sự đang có trong đầu: *"tôi có hợp **đơn này** không, và nếu chưa thì thiếu
gì"* — vì họ vừa đọc xong một đơn cụ thể trên website.

Hai cửa dùng chung một bộ đối chiếu. Không có engine thứ hai, không có bảng điểm
thứ hai. Danh mục đem đối chiếu ở đây chỉ có đúng một đơn.

## Khác gì với khung chat

Khung chat là phần **phụ trợ**: hỏi đáp chung theo tài liệu của công ty. Nó không
biết khách đang xem đơn nào, và không cần biết. Phòng tư vấn là hệ riêng, có dữ
liệu của khách và kết quả đối chiếu trong tay.

## Cho đối chiếu trên hồ sơ chưa xác nhận, nhưng không cho đăng ký

Ứng viên gửi CV xong là muốn biết ngay mình có hợp không. Bắt họ đi qua bước xem
lại và xác nhận từng dòng trước khi được biết bất cứ điều gì là dựng một cánh cửa
ở chỗ không cần cửa — họ đang ngồi trước máy, câu hỏi thì hẹp.

Nhưng **đăng ký** vẫn đòi hồ sơ đã xác nhận. Máy có thể đọc nhầm; tạo hồ sơ đăng
ký từ chỗ đọc nhầm là đẩy cái sai sang cho nhân viên gọi điện. Chốt chặn nằm ở
`advice.Advice.can_register`, và luồng đăng ký vẫn kiểm lại độc lập.
"""
from typing import Annotated, Any

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from app.advisor import client as advisor_client
from app.advisor import phrasing, qa
from app.auth.journey_security import require_journey_session
from app.auth.security import get_current_user
from app.core.config import settings
from app.core.timeutil import utc_now
from app.consultation import advice as advice_builder
from app.consultation import context_builder, eligibility, order_context
from app.memory import render as bo_nho_render
from app.memory import topics
from app.core.rate_limit import client_ip, rate_limiter
from app.core.session_id import SESSION_PATTERN
from app.db import advisor_turns
from app.db import candidate_profiles as profiles
from app.db import courses, job_orders
from app.db import session_memory
from app.matching import explain
from app.services import matching_service


public_router = APIRouter(
    # Tiền tố riêng, có số phiên bản. Tách khỏi `/public/*` để nhìn danh sách
    # đường là biết ngay đâu là hệ chính, đâu là phụ trợ — và để sau này đổi
    # hình dạng dữ liệu mà không làm gãy bản đang chạy.
    prefix="/tu-van/v1",
    tags=["Engine tư vấn"],
    dependencies=[Depends(require_journey_session)],
)

router = APIRouter(
    prefix="/advisor",
    tags=["Engine tư vấn (nội bộ)"],
    dependencies=[Depends(get_current_user)],
)

ORDER_PATTERN = r"^DH-\d{4,6}$"


@router.get("/thong-ke")
async def thong_ke_bot(
    so_ngay: int = Query(default=30, ge=1, le=365),
    current_user=Depends(get_current_user),
) -> dict[str, Any]:
    """Số liệu độ tin được của bot tư vấn.

    Trả lời câu *"làm sao biết bot không bịa"* bằng đo đạc: bao nhiêu lượt mô
    hình trả lời, bao nhiêu lượt bot chịu nói không biết, và tỉ lệ giữa hai bên.

    Tỉ lệ `khong_doan` cao **không phải là hỏng**. Nó có nghĩa là chốt hậu kiểm
    đang làm việc, hoặc ứng viên đang hỏi những thứ nằm ngoài hồ sơ và đơn — cả
    hai đều là hành vi mong muốn. Con số đáng lo là tỉ lệ ấy bằng không: khi đó
    hoặc chưa ai dùng, hoặc chốt chặn đã bị tắt mất.
    """
    moc = utc_now() - timedelta(days=so_ngay)
    return {
        "so_ngay": so_ngay,
        **await advisor_turns.thong_ke(since=moc),
        # Tình trạng hạn mức phải nằm cạnh số liệu, không chỉ nằm trong log máy
        # chủ. Người đọc bảng này cần biết một tỉ lệ "không đoán" tăng vọt có thể
        # chỉ là do hết hạn mức dùng chung, chứ không phải bot đang thận trọng.
        "dung_chung_han_muc": advisor_client.dung_chung_khoa(),
        "engine_bat": settings.advisor_enabled,
        # Chủ đề ứng viên hỏi nhiều nhất, gộp từ CẢ HAI chỗ biết nói chuyện.
        # Đây là số liệu nghiệp vụ chứ không phải kỹ thuật: chi phí đứng đầu bảng
        # nghĩa là trang giới thiệu đang nói chưa đủ rõ về chi phí — và đó là
        # việc sửa được, khác hẳn với việc đổ cho ứng viên không chịu đọc.
        "moi_quan_tam": await session_memory.thong_ke(since=moc),
    }


@public_router.get("/dieu-kien")
async def dieu_kien_chuong_trinh() -> dict[str, Any]:
    """Điều kiện mức nền, không phụ thuộc phiên hay đơn nào.

    Tách riêng để trang giới thiệu dùng được mà không phải mở phiên tư vấn.
    """
    return eligibility.as_dict()


@public_router.get("/{session_id}/don/{code}")
async def tu_van_theo_don(
    session_id: Annotated[str, Path(pattern=SESSION_PATTERN)],
    code: Annotated[str, Path(pattern=ORDER_PATTERN)],
    http_request: Request,
    dien_dat: bool = True,
) -> dict[str, Any]:
    """Đối chiếu hồ sơ của phiên với đúng một đơn, rồi phân nhánh tư vấn.

    `dien_dat=false` bỏ qua lớp mô hình ngôn ngữ và chỉ trả bản ghép sẵn — dùng
    khi cần kết quả hoàn toàn tất định, ví dụ lúc chạy kiểm thử hoặc khi trình
    bày cho hội đồng xem hai bản cạnh nhau.
    """
    # Giới hạn theo IP. Mỗi lượt gọi có thể kéo theo một lần gọi mô hình, nên
    # đây cũng là hàng rào giữ hạn mức Gemini.
    rate_limiter.check(f"tu-van-don:{client_ip(http_request)}", limit=30, window_seconds=60)

    profile = await profiles.get_by_session(session_id)
    if profile is None:
        raise HTTPException(
            status_code=404,
            detail="Chưa có hồ sơ cho phiên này. Bạn gửi CV hoặc khai nhanh vài mục nhé.",
        )

    try:
        log, da_dung_lai = await matching_service.run_matching(
            profile, trigger="tu_van_theo_don", chi_don=code
        )
    except matching_service.DonKhongCo:
        raise HTTPException(
            status_code=404,
            detail="Đơn này hiện không còn nhận hồ sơ. Bạn xem đơn khác giúp mình nhé.",
        ) from None

    item = _dong_cua_don(log, code)

    ket_qua = advice_builder.build(
        _thanh_match_item(item),
        required_japanese=await _yeu_cau_tieng_nhat(code),
        profile_level=_trinh_do(profile),
        courses=await courses.list_published(),
        profile_confirmed=profile.get("status") == profiles.STATUS_CONFIRMED,
    )

    # Bản ghép sẵn luôn có. Bản mô hình viết lại chỉ là thêm vào, và nếu nó bị
    # chốt chặn loại thì màn hình vẫn đủ chữ.
    van_ban = explain.render_template_text(_thanh_match_item(item))
    van_ban_ai = await phrasing.rephrase(ket_qua.block) if dien_dat else None

    # Mở màn hình tư vấn của một đơn là hành vi rõ ràng nhất cho biết khách đang
    # quan tâm đơn nào. Ghi vào bộ nhớ chung để khung chat ở góc màn hình thôi
    # phải đoán đơn bằng cách dò tên tỉnh trong câu hỏi.
    await session_memory.dat_don_dang_xet(session_id, code)

    return {
        **advice_builder.as_dict(ket_qua),
        "text": van_ban_ai or van_ban,
        # Nói rõ câu đang hiện do ai viết. Hội đồng sẽ hỏi đúng chỗ này, và người
        # dùng cũng nên biết mình đang đọc câu máy ghép hay câu mô hình viết.
        "text_source": "mo_hinh" if van_ban_ai else "ghep_san",
        "text_template": van_ban,
        "recommendation_log_code": log["code"],
        "reused": da_dung_lai,
        "suc_khoe": eligibility.as_dict(),
    }


class CauHoiBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=2, max_length=500)


@public_router.get("/{session_id}/don/{code}/hoi")
async def lich_su_hoi_dap(
    session_id: Annotated[str, Path(pattern=SESSION_PATTERN)],
    code: Annotated[str, Path(pattern=ORDER_PATTERN)],
) -> dict[str, Any]:
    """Các lượt đã hỏi về đơn này. Tải lại trang không mất cuộc trò chuyện."""
    return {"items": await advisor_turns.list_turns(session_id, code)}


@public_router.post("/{session_id}/don/{code}/hoi")
async def hoi_them(
    session_id: Annotated[str, Path(pattern=SESSION_PATTERN)],
    code: Annotated[str, Path(pattern=ORDER_PATTERN)],
    payload: CauHoiBody,
    http_request: Request,
) -> dict[str, Any]:
    """Hỏi bot về hồ sơ của mình và đơn đang xem.

    Bot **không có kho tài liệu nào**. Nó chỉ đọc bốn khối chữ do quy tắc dựng:
    hồ sơ, đơn, kết quả đối chiếu, điều kiện mức nền. Câu hỏi ngoài bốn khối ấy
    thì nó nói thẳng là chưa có thông tin và chỉ sang khung chat hoặc nhân viên.

    Đây là tính năng chứ không phải giới hạn: kho tài liệu hiện còn rác nhận dạng
    ảnh ở hai mươi bốn trên ba mươi hai đoạn, đủ để một câu trả lời về chi phí
    nói sai con số — mà con số ấy sẽ được đọc như lời của công ty.
    """
    rate_limiter.check(f"tu-van-hoi:{client_ip(http_request)}", limit=20, window_seconds=300)

    if await advisor_turns.count_turns(session_id, code) >= advisor_turns.MAX_MOI_PHIEN:
        raise HTTPException(
            status_code=429,
            detail=(
                "Cuộc trao đổi về đơn này đã khá dài. Bạn để lại tin nhắn cho "
                "nhân viên tư vấn để được trả lời kỹ hơn nhé."
            ),
        )

    profile = await profiles.get_by_session(session_id)
    if profile is None:
        raise HTTPException(
            status_code=404,
            detail="Chưa có hồ sơ cho phiên này. Bạn gửi CV hoặc khai nhanh vài mục nhé.",
        )

    don = await job_orders.get_job_order(code)
    if don is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn này.")

    # Dựng lại đúng khối đối chiếu khách đang nhìn thấy, để bot và màn hình nói
    # cùng một điều. Lấy từ nhật ký thay vì tính lại: tính lại có thể ra kết quả
    # khác nếu hồ sơ vừa đổi, và khi ấy bot trả lời về một thứ khách không thấy.
    try:
        log, _ = await matching_service.run_matching(
            profile, trigger="tu_van_hoi_them", chi_don=code
        )
        item = _dong_cua_don(log, code)
        ket_qua = advice_builder.build(
            _thanh_match_item(item),
            required_japanese=(don.get("requirements") or {}).get("japanese_required"),
            profile_level=_trinh_do(profile),
            courses=await courses.list_published(),
            profile_confirmed=profile.get("status") == profiles.STATUS_CONFIRMED,
        )
        khoi_doi_chieu = ket_qua.block
    except matching_service.DonKhongCo:
        khoi_doi_chieu = ""

    # Ghi vào bộ nhớ chung TRƯỚC khi hỏi mô hình, để khung chat thấy được ngay
    # cả khi lượt này hỏng giữa chừng. Ghi sau thì mỗi lần mô hình lỗi là một lần
    # mất dấu vết việc khách đã hỏi.
    chu_de = topics.phan_loai(payload.question)
    if chu_de:
        await session_memory.ghi_moi_quan_tam(
            session_id,
            chu_de=chu_de,
            cau_hoi=payload.question,
            ben=session_memory.BEN_TU_VAN,
        )

    profiles.decorate(profile)
    cau, nguon, model = await qa.tra_loi(
        cau_hoi=payload.question,
        ho_so=context_builder.render(profile),
        don=order_context.render(don),
        doi_chieu=khoi_doi_chieu,
        dieu_kien_nen=eligibility.render_muc_nen(),
        bo_nho=bo_nho_render.render(
            await session_memory.lay(session_id), cho=session_memory.BEN_TU_VAN
        ),
        lich_su=await advisor_turns.list_turns(session_id, code, limit=qa.SO_LUOT_NHO),
    )

    # Chỉ đánh dấu "đã giải thích" khi mô hình thật sự trả lời được. Đánh dấu cả
    # lúc bot nói không biết thì khung chat sẽ tưởng chủ đề đã xong và cũng lảng
    # sang chuyện khác — khách hỏi hai nơi, không nơi nào trả lời.
    if chu_de and nguon == qa.NGUON_MO_HINH:
        await session_memory.ghi_da_giai_thich(
            session_id, chu_de=chu_de, ben=session_memory.BEN_TU_VAN
        )

    luot = await advisor_turns.add_turn(
        session_id=session_id,
        job_order_code=code,
        question=payload.question.strip(),
        answer=cau,
        source=nguon,
        model=model,
    )
    return {"question": luot["question"], "answer": cau, "source": nguon}


def _dong_cua_don(log: dict[str, Any], code: str) -> dict[str, Any]:
    for row in log.get("items") or ():
        if row.get("code") == code:
            return row
    # Không xảy ra nếu `chi_don` đã lọc đúng, nhưng im lặng trả rỗng ở đây sẽ
    # thành một màn hình trống không ai hiểu vì sao.
    raise HTTPException(status_code=500, detail="Không dựng được kết quả đối chiếu cho đơn này.")


async def _yeu_cau_tieng_nhat(code: str) -> str | None:
    """Mức tiếng Nhật đơn yêu cầu — để dựng lộ trình học.

    Phải tra lại bản ghi đơn vì nhật ký giới thiệu **không lưu** khối
    `requirements`: `MatchItem` chỉ giữ các dòng tiêu chí đã chấm, không giữ dữ
    liệu gốc của đơn. Đọc `requirement_text` của dòng tiếng Nhật rồi bóc chữ
    "N4" ra khỏi câu cũng được, nhưng đó là phân tích câu chữ hiển thị — đổi
    cách viết nhãn một lần là lộ trình học lặng lẽ sai.

    Đơn có thể đã đổi giữa lúc đối chiếu và lúc gọi hàm này. Khoảng lệch ấy tính
    bằng giây, và nếu đơn đổi thật thì dấu vân tay danh mục đổi theo nên lần đối
    chiếu kế tiếp tự chạy lại.
    """
    don = await job_orders.get_job_order(code)
    if don is None:
        return None
    return (don.get("requirements") or {}).get("japanese_required")


def _trinh_do(profile: dict[str, Any]) -> str | None:
    return ((profile.get("fields") or {}).get("japanese_level") or {}).get("value")


def _thanh_match_item(row: dict[str, Any]):
    """Dựng lại `MatchItem` từ dòng nhật ký đã lưu.

    Nhật ký lưu dạng dict để tuần tự hóa được; `advice` và `explain` thì nhận
    `MatchItem`. Dựng lại ở đây thay vì để hai module kia nhận cả hai kiểu —
    nhận hai kiểu là chỗ sinh lỗi im lặng khi một bên đổi hình dạng.
    """
    from app.matching.engine import CriterionRow, MatchItem, SoftRow

    return MatchItem(
        code=row.get("code") or "",
        title=row.get("title") or "",
        employer_name=row.get("employer_name") or "",
        prefecture=row.get("prefecture") or "",
        region_group=row.get("region_group"),
        employer_type=row.get("employer_type") or "",
        program=row.get("program") or "",
        deadline=row.get("deadline") or "",
        eligible=bool(row.get("eligible")),
        score=int(row.get("score") or 0),
        rank=row.get("rank"),
        hard_rows=tuple(CriterionRow(**dong) for dong in row.get("hard_rows") or ()),
        soft_rows=tuple(SoftRow(**dong) for dong in row.get("soft_rows") or ()),
        gaps=tuple(row.get("gaps") or ()),
        missing_info=tuple(row.get("missing_info") or ()),
        labels=row.get("labels") or {},
    )
