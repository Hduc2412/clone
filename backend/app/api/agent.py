"""Đường API của Agent điều phối — phòng tư vấn cấp **hồ sơ**.

## Khác gì phòng tư vấn theo đơn

`/tu-van/v1/{session}/don/{code}/hoi` trả lời câu *"tôi có hợp **đơn này** không"*.
Hẹp, và thường là câu người ta có trong đầu khi vừa đọc một đơn.

Đường ở đây trả lời câu rộng hơn: *"hồ sơ của tôi thế nào, tôi nên làm gì tiếp"*.
Nó không gắn với đơn nào, nhưng **biết** đơn khách đang xem nếu có — lấy từ bộ
nhớ phiên, do một hành vi thật (mở màn hình đơn đó) ghi vào, không phải do mô
hình khai.

Hai phòng dùng chung bộ lưu lượt (`advisor_turns`) với hai phạm vi tách nhau:
phòng theo đơn mang mã đơn, phòng hồ sơ mang `None`.

## Vì sao `mo-dau` là POST chứ không phải GET

Nó **ghi**: lưu một lượt vào `advisor_turns` và cập nhật mốc tư vấn trong bộ nhớ
phiên. Để GET thì trình duyệt và proxy được phép gọi lại tùy ý, và mỗi lần tải
lại trang sẽ sinh thêm một lượt mở đầu trong lịch sử.

Gọi hai lần cũng không sinh hai lượt: lượt mở đầu của mỗi mốc chỉ ghi một lần,
xem `_da_mo_dau`.
"""
import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Path, Request
from pydantic import BaseModel, ConfigDict, Field

from app.agent import ban_giao as ban_giao_builder
from app.agent import contract, mo_dau, orchestrator, state
from app.auth.journey_security import require_journey_session
from app.core.rate_limit import client_ip, rate_limiter
from app.core.session_id import SESSION_PATTERN
from app.db import advisor_turns
from app.db import candidate_documents as tai_lieu_cv
from app.db import candidate_profiles as profiles
from app.db import recommendation_logs, session_memory, support_requests
from app.db.database import (
    list_appointments_for_session,
    list_unassigned_registrations,
)
from app.matching import catalog, explain
from app.services import matching_service


logger = logging.getLogger(__name__)

public_router = APIRouter(
    prefix="/tu-van/v1",
    tags=["Agent tư vấn"],
    dependencies=[Depends(require_journey_session)],
)

# Hai mốc Agent chủ động nói. Chuỗi nằm trong API nên đổi là đổi hợp đồng.
MOC_SAU_CV = "sau_cv"
MOC_SAU_MATCHING = "sau_matching"
CAC_MOC = (MOC_SAU_CV, MOC_SAU_MATCHING)


class CauHoiBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=2, max_length=500)


class MoDauBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    moc: str = Field(pattern=r"^(sau_cv|sau_matching)$")


class XacNhanBody(BaseModel):
    """Ứng viên xác nhận một điều Agent nghe được.

    Chỉ nhận **tên trường và giá trị**, không nhận `source`: nguồn do máy chủ
    quyết. Trình duyệt gửi `source: "staff"` lên thì giá trị ấy sẽ đè lên dữ liệu
    nhân viên vừa chốt, và đó là một đường leo quyền mở sẵn.
    """

    model_config = ConfigDict(extra="forbid")

    field: str = Field(min_length=2, max_length=40)
    value: Any


async def _nap(session_id: str) -> tuple[dict[str, Any] | None, state.TrangThai, dict[str, Any] | None]:
    """Đọc mọi thứ cần để suy trạng thái. Trả `(hồ sơ, trạng thái, nhật ký)`.

    Đọc song song được, nhưng ở đây đọc lần lượt cho dễ đọc mã: bốn lời gọi nhỏ
    trên cùng một database, và đường này không nằm trên đường găng nào.
    """
    profile = await profiles.get_by_session(session_id)

    log = None
    if profile:
        log = await recommendation_logs.latest_for_profile(profile["code"])

    bo_nho = await session_memory.lay(session_id)
    don_dang_xet = (bo_nho or {}).get("job_order_code")

    yeu_cau = await support_requests.list_for_session(session_id)
    dang_mo = tuple(
        r["code"] for r in yeu_cau if r.get("dang_mo") and r.get("code")
    )

    # `include_assigned=True` bắt buộc: mặc định hàm này chỉ lấy hồ sơ **chưa ai
    # nhận**, vì đó là định nghĩa của hàng đợi nhân viên. Ở đây câu hỏi khác —
    # "ứng viên đã đăng ký đơn nào" — và một hồ sơ vừa được nhân viên nhận thì
    # vẫn là đã đăng ký. Thiếu cờ này là Agent nói "bạn chưa đăng ký đơn nào" với
    # người có nhân viên đang gọi cho họ.
    ho_so_tuyen = await list_unassigned_registrations(
        session_id=session_id, include_assigned=True
    )
    da_dang_ky = tuple(
        r["job_order_code"] for r in ho_so_tuyen or () if r.get("job_order_code")
    )

    trang_thai = state.suy_ra(
        profile=profile,
        log=log,
        don_dang_xet=don_dang_xet,
        don_da_dang_ky=da_dang_ky,
        yeu_cau_dang_mo=dang_mo,
    )
    return profile, trang_thai, log


@public_router.get("/{session_id}/tro-ly")
async def trang_thai_tro_ly(
    session_id: Annotated[str, Path(pattern=SESSION_PATTERN)],
) -> dict[str, Any]:
    """Trạng thái Agent. **Không gọi mô hình**, nên gọi bao nhiêu lần cũng được.

    Giao diện dựng toàn bộ phần tĩnh của phòng tư vấn từ đường này: giai đoạn,
    trường còn thiếu, nút gợi ý, câu hỏi bấm được. Chỉ khi ứng viên gõ một câu
    thì mới tới lượt mô hình.
    """
    profile, trang_thai, _log = await _nap(session_id)
    luot = await advisor_turns.list_turns(session_id, None)
    return {
        **trang_thai.as_dict(),
        "suggested_questions": orchestrator.cau_hoi_con_thieu(profile),
        "turns": luot,
    }


@public_router.post("/{session_id}/tro-ly/mo-dau")
async def mo_dau_hoi_thoai(
    session_id: Annotated[str, Path(pattern=SESSION_PATTERN)],
    payload: MoDauBody,
) -> dict[str, Any]:
    """Lượt Agent chủ động nói. Dựng bằng template, không gọi mô hình.

    Không gọi mô hình ở đây là quyết định về hạn mức, không phải về chất lượng:
    hai lượt này xuất hiện với **mọi** ứng viên, nên nếu chúng tốn một lượt gọi
    thì mười ứng viên là hết hạn mức của cả ngày. Xem `app/agent/__init__.py`.
    """
    profile, trang_thai, log = await _nap(session_id)

    khoa: str | None = None
    if payload.moc == MOC_SAU_CV:
        tai_lieu = await _tep_cv_moi_nhat(session_id)
        van_ban = mo_dau.sau_khi_doc_cv(profile, nguon=mo_dau.nguon_ho_so(tai_lieu))
        khoa = _khoa_mo_dau(tai_lieu)
    else:
        van_ban = mo_dau.sau_matching(log, profile=profile)

    # Tải lại trang, hay sửa hồ sơ, không sinh thêm một lượt mở đầu nữa.
    if not await _da_mo_dau(session_id, van_ban, khoa=khoa):
        await advisor_turns.add_turn(
            session_id=session_id,
            job_order_code=None,
            question=f"{ban_giao_builder.NHAN_HE_THONG} {payload.moc}",
            answer=van_ban,
            source=advisor_turns.SOURCE_MO_HINH,
            model="ghep_san",
            moc=khoa,
        )
        await _ghi_moc(session_id, trang_thai)

    return {
        "reply": van_ban,
        # Nói rõ câu này do mã ghép, không phải mô hình viết. Cùng khuôn với
        # `text_source` ở phòng tư vấn theo đơn.
        "text_source": "ghep_san",
        **trang_thai.as_dict(),
        "suggested_questions": orchestrator.cau_hoi_con_thieu(profile),
    }


@public_router.get("/{session_id}/tro-ly/hoi")
async def lich_su_cap_ho_so(
    session_id: Annotated[str, Path(pattern=SESSION_PATTERN)],
) -> dict[str, Any]:
    """Các lượt đã trao đổi ở cấp hồ sơ. Tải lại trang không mất hội thoại."""
    return {"items": await advisor_turns.list_turns(session_id, None)}


@public_router.post("/{session_id}/tro-ly/hoi")
async def hoi_tro_ly(
    session_id: Annotated[str, Path(pattern=SESSION_PATTERN)],
    payload: CauHoiBody,
    http_request: Request,
) -> dict[str, Any]:
    """Hỏi Agent về toàn bộ hồ sơ và kết quả đối chiếu."""
    rate_limiter.check(
        f"tro-ly-hoi:{client_ip(http_request)}", limit=20, window_seconds=300
    )

    if await advisor_turns.count_turns(session_id, None) >= advisor_turns.MAX_MOI_PHIEN:
        raise HTTPException(
            status_code=429,
            detail=(
                "Cuộc trao đổi đã khá dài. Bạn để lại tin nhắn cho nhân viên tư "
                "vấn để được trả lời kỹ hơn nhé."
            ),
        )

    profile, trang_thai, log = await _nap(session_id)
    if profile is None:
        raise HTTPException(
            status_code=404,
            detail="Chưa có hồ sơ cho phiên này. Bạn gửi CV hoặc khai nhanh vài mục nhé.",
        )

    profiles.decorate(profile)
    khoi = _khoi_doi_chieu(log)

    ket_qua, nguon, model = await orchestrator.tra_loi(
        cau_hoi=payload.question,
        profile=profile,
        trang_thai=trang_thai,
        khoi_doi_chieu=khoi,
        lich_su=await advisor_turns.list_turns(
            session_id, None, limit=orchestrator.SO_LUOT_NHO
        ),
        bo_nho=await session_memory.lay(session_id),
    )

    await advisor_turns.add_turn(
        session_id=session_id,
        job_order_code=None,
        question=payload.question.strip(),
        answer=ket_qua.reply,
        source=nguon,
        model=model,
    )
    await _ghi_moc(session_id, trang_thai)

    return {
        "question": payload.question.strip(),
        "answer": ket_qua.reply,
        "source": nguon,
        **ket_qua.as_dict(),
        **trang_thai.as_dict(),
    }


@public_router.post("/{session_id}/tro-ly/xac-nhan")
async def xac_nhan_de_xuat(
    session_id: Annotated[str, Path(pattern=SESSION_PATTERN)],
    payload: XacNhanBody,
) -> dict[str, Any]:
    """Ứng viên xác nhận một điều Agent nghe được trong hội thoại.

    Đây là **đường duy nhất** để nội dung hội thoại vào hồ sơ, và nó đòi một cú
    bấm của người dùng. Mô hình không có đường nào đi tắt qua đây.

    Nguồn ghi là `user_confirmed`, không phải `chat`: người dùng vừa đọc đúng giá
    trị đó trên màn hình và bấm đồng ý — đó là một lần xác nhận thật, không khác
    gì xác nhận một ô trên biểu mẫu.
    """
    profile = await profiles.get_by_session(session_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Chưa có hồ sơ cho phiên này.")

    # Kiểm lại từ đầu, không tin gì vào việc "Agent đã đề xuất nó rồi".
    #
    # Đề xuất không được lưu ở đâu cả, nên không có cách nào đối chứng rằng giá
    # trị đang gửi lên đúng là giá trị Agent đã nêu. Nên đường này phải tự đứng
    # được: trường có trong danh sách cho phép, kiểu dữ liệu đúng — y như đường
    # biểu mẫu. Người gọi trực tiếp bằng curl cũng chỉ làm được đúng những gì
    # biểu mẫu làm được.
    nhan, loai = contract.kiem_de_xuat(
        [{"field": payload.field, "value": payload.value}],
        profile=profile,
        # Nguồn sắp ghi là `user_confirmed`, không phải `chat`. Thiếu tham số này
        # thì phép kiểm "đã có nguồn đáng tin hơn" so với `chat`, và đường này từ
        # chối mọi lần ứng viên sửa một trường máy đọc từ CV — đúng việc nó tồn
        # tại để làm. Nguồn `staff` thì vẫn chặn, vì nó xếp trên `user_confirmed`.
        nguon_se_ghi="user_confirmed",
    )
    if not nhan:
        raise HTTPException(
            status_code=400,
            detail=loai[0] if loai else "Giá trị không hợp lệ.",
        )

    muc = nhan[0]
    phan = {muc.muc: {muc.field: muc.value}}
    # Tỉnh kéo theo vùng — cùng quy tắc với biểu mẫu (`PreferencesPayload._derive_region`).
    # Kiểm trên trình duyệt ngày 06/10: xác nhận "Tokyo" qua trợ lý xong, hồ sơ vẫn
    # không có vùng, nên đơn ở Kanagawa (cùng Kantō, đáng +25) chấm ngang đơn ở
    # Fukuoka cho tới khi khách tình cờ gửi lại biểu mẫu. Đổi tỉnh mà giữ vùng cũ
    # thì hai ô nói hai nơi khác nhau, nên vùng luôn đi theo tỉnh vừa xác nhận.
    if muc.field == "desired_prefecture" and isinstance(muc.value, str):
        vung = catalog.region_for_prefecture(muc.value)
        if vung:
            phan.setdefault("preferences", {})["desired_region_group"] = vung
    da_sua = await _ghi_mot_truong(session_id, profile, phan)
    if da_sua is None:
        raise HTTPException(
            status_code=409,
            detail="Hồ sơ vừa được cập nhật ở nơi khác. Bạn tải lại trang giúp mình nhé.",
        )
    return profiles.decorate(da_sua)


@public_router.get("/{session_id}/tro-ly/ban-giao")
async def ban_giao_cho_nhan_vien(
    session_id: Annotated[str, Path(pattern=SESSION_PATTERN)],
) -> dict[str, Any]:
    """Bản tóm tắt sẽ đi kèm khi chuyển cho nhân viên.

    Cho ứng viên xem trước, có chủ ý: họ sắp gửi một bản mô tả về chính mình cho
    một người sẽ gọi điện: họ có quyền đọc nó trước. Và nếu có dòng nào sai thì
    đây là lúc rẻ nhất để sửa.
    """
    profile, trang_thai, log = await _nap(session_id)
    return {
        "summary": ban_giao_builder.dung(
            profile=profile,
            trang_thai=trang_thai,
            log=log,
            # Cùng một bản bàn giao thì cùng một tập dữ liệu. Đường này cho
            # khách xem trước đúng thứ nhân viên sẽ đọc — lệch một dòng là lời
            # hứa "xem trước" thành sai.
            luot_hoi=await advisor_turns.list_all_turns(session_id),
            # Lịch hẹn: thứ duy nhất trong bản bàn giao có mốc thời gian,
            # nên nó quyết định thứ tự việc trong ngày của nhân viên.
            lich_hen=await list_appointments_for_session(session_id),
        ),
        **trang_thai.as_dict(),
    }


def _khoi_doi_chieu(log: dict[str, Any] | None) -> str:
    """Khối kết quả đối chiếu cho mô hình đọc — và cũng là khối chốt số so vào.

    Dựng từ **nhật ký đã lưu**, không đối chiếu lại: tính lại có thể ra kết quả
    khác nếu hồ sơ vừa đổi, và khi ấy Agent trả lời về một thứ ứng viên không
    thấy trên màn hình.
    """
    if log is None:
        return ""
    dong: list[str] = ["[Kết quả đối chiếu hồ sơ với các đơn]"]
    dat = [r for r in log.get("items") or () if r.get("eligible")]
    dong.append(
        f"Đã xét {log.get('total_considered') or len(log.get('items') or ())} đơn, "
        f"đủ điều kiện {len(dat)} đơn."
    )
    for row in dat[:5]:
        dong.append("")
        dong.append(explain.render_block(matching_service._rebuild(row)))
    return "\n".join(dong)


async def _tep_cv_moi_nhat(session_id: str) -> dict[str, Any] | None:
    """Tệp CV gửi gần nhất của phiên, hoặc `None` nếu khách chỉ khai tay."""
    cac_tep = await tai_lieu_cv.list_for_session(session_id)
    return cac_tep[0] if cac_tep else None


def _khoa_mo_dau(tai_lieu: dict[str, Any] | None) -> str:
    """Khóa chống trùng của lượt "sau CV": **một lượt cho mỗi tệp**, hoặc một lượt
    cho cả phiên nếu khách khai tay.

    Không so theo chữ như lượt sau đối chiếu. Chữ của lượt này phụ thuộc nguồn
    từng trường, mà "Sửa hồ sơ" ghi lại mọi trường thành `user_confirmed` — chữ
    đổi, nên bản so-theo-chữ ghi thêm một lượt mở đầu thứ hai ngay sau khi khách
    sửa (bắt trên trình duyệt ngày 06/10). Lượt này nói về **việc gửi tệp**; gửi
    tệp mới mới là lúc nói lại.
    """
    return f"{MOC_SAU_CV}:{tai_lieu['code'] if tai_lieu else mo_dau.KHAI_TAY}"


async def _da_mo_dau(session_id: str, van_ban: str, *, khoa: str | None = None) -> bool:
    """Lượt mở đầu này đã ghi rồi chưa.

    Lượt sau đối chiếu (`khoa=None`) so theo nội dung: kết quả đổi thì câu đổi
    theo, và khách vừa sửa hồ sơ thì nên được nghe lại bản tóm tắt kết quả mới.

    Lượt sau CV so theo `khoa` — xem `_khoa_mo_dau`. Lượt sau CV ghi **trước**
    khi có khóa thì không mang khóa nào; coi như đã mở đầu, để phiên cũ tải lại
    trang không bị nói lại lần nữa.
    """
    for l in await advisor_turns.list_turns(session_id, None):
        if khoa is None:
            if l.get("answer") == van_ban:
                return True
            continue
        if l.get("moc") == khoa:
            return True
        if not l.get("moc") and l.get("question") == f"{ban_giao_builder.NHAN_HE_THONG} {MOC_SAU_CV}":
            return True
    return False


async def _ghi_moc(session_id: str, trang_thai: state.TrangThai) -> None:
    """Mốc tư vấn vào bộ nhớ chung — **một dòng trạng thái, không có nội dung**.

    Đây là mức thứ hai của "hai mức bộ nhớ": bản tóm tắt đầy đủ đi kèm yêu cầu
    hỗ trợ cho nhân viên đọc, còn bộ nhớ chung chỉ nhận một mốc kiểu "đã tư vấn
    tới bước đối chiếu, đang xem DH-0001".

    Vì sao chỉ một dòng: bộ nhớ chung được **khung chat đọc**, và khung chat chỉ
    làm hỏi đáp chung theo tài liệu công ty. Đưa nội dung tư vấn vào đó là để nó
    trả lời sâu về hồ sơ và matching bằng một kho tài liệu còn rác nhận dạng ảnh
    ở 24/32 đoạn — đúng chỗ dễ nói sai con số nhất. Xem `app/memory/__init__.py`.
    """
    try:
        await session_memory.ghi_moc_tu_van(
            session_id,
            giai_doan=trang_thai.stage,
            nhan=state.NHAN.get(trang_thai.stage, trang_thai.stage),
        )
    except Exception:  # noqa: BLE001
        # Bộ nhớ chung là phần thêm vào. Hỏng nó không được làm hỏng một lượt tư
        # vấn vốn đã trả lời xong và đã lưu.
        logger.warning("Không ghi được mốc tư vấn vào bộ nhớ phiên", exc_info=True)


async def _ghi_mot_truong(
    session_id: str,
    profile: dict[str, Any],
    phan: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    """Ghi một trường đã được người dùng xác nhận, có kiểm phiên bản.

    Luôn dựng **cả hai phần**, kể cả phần không đổi.

    Bản trước chỉ dựng phần đang sửa rồi truyền `merged.get(...)` cho phần kia —
    tức `None`. Và `apply_changes` lúc ấy ghi thẳng `None` vào database, nên xác
    nhận một trường thuộc `fields` **xoá sạch nguyện vọng** của ứng viên.

    Hỏng còn tệ hơn mất dữ liệu: nó chỉ nổ ở một bước khác, sau vài cú bấm nữa —
    bước xác nhận hồ sơ trả 500 và giao diện hiện "Không kết nối được máy chủ",
    một câu chỉ sai hướng hoàn toàn. Gặp thật trên luồng gửi CV ngày 05/10.

    Cửa ghi nay coi `None` là "giữ nguyên phần này", nên lỗi ấy không lặp lại
    được. Dù vậy ở đây vẫn dựng tường minh cả hai phần: dựa vào ngữ nghĩa mặc
    định của hàm khác để che một chỗ mình biết là thiếu thì lần sau đọc lại không
    ai thấy ý định.
    """
    merged: dict[str, Any] = {}
    for muc in ("fields", "preferences"):
        cho_phep = (
            profiles.FIELD_KEYS if muc == "fields" else profiles.PREFERENCE_KEYS
        )
        hop_nhat, _doi = profiles.merge_section(
            profile.get(muc), phan.get(muc) or {}, source="user_confirmed", allowed=cho_phep
        )
        merged[muc] = hop_nhat

    return await profiles.apply_changes(
        session_id,
        expected_version=profile.get("version", 1),
        fields=merged.get("fields"),
        preferences=merged.get("preferences"),
        history=profiles.history_entry(
            profile, "user_confirmed", "Xác nhận điều trợ lý nghe được"
        ),
        # KHÔNG đổi `status`. Xác nhận một trường lẻ không phải là xác nhận cả hồ
        # sơ — bước ấy có đường riêng (`/public/profiles/{session}/confirm`) và
        # nó kiểm những trường bắt buộc. Nhảy tắt qua đây là mở đường đăng ký
        # trên một hồ sơ chưa ai xem lại.
        status=None,
    )
