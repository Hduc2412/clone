"""Một lượt của Agent: dựng ngữ cảnh → gọi mô hình → hậu kiểm → trả hợp đồng.

## Một lời gọi mô hình, không phải hai

Cách hiển nhiên là gọi hai lần: một lần xin câu trả lời, một lần xin khối dữ liệu
có cấu trúc. Nó nhân đôi chi phí hạn mức, mà hạn mức là 20 lượt mỗi ngày.

Nên ở đây xin **một khối JSON có trường `reply` bên trong**, rồi bóc ra. Cái giá
phải trả là mô hình có thể trả về chữ không đúng định dạng — và đường thoát cho
việc đó nằm ngay dưới: không bóc được JSON thì coi toàn bộ câu trả lời là `reply`
và đi tiếp. Thà mất phần cấu trúc hơn mất cả lượt.

## Chốt chặn chạy trên `reply`, và nếu `reply` bị loại thì bỏ luôn phần cấu trúc

`qa.kiem_tra` là bộ bảy chốt đã chạy từ 29/09: chốt số, chốt hứa hẹn, chốt cam
kết, chốt câu dở, chốt mở rộng phạm vi. Nó soi **văn bản**, nên phải gọi trên
đúng trường `reply` chứ không gọi trên cả khối JSON — khối JSON không bao giờ kết
thúc bằng dấu chấm, nên chốt câu dở sẽ loại mọi lượt.

Điều quan trọng hơn: `reply` bị loại thì **`facts_to_save` cũng bị bỏ**. Một mô
hình vừa bịa một con số trong câu trả lời thì không có lý gì để tin phần nó nghe
được trong hội thoại. Hai phần đến từ cùng một lượt sinh, nên chúng đứng hoặc đổ
cùng nhau.

## Agent đọc được giai đoạn, không ghi được

`state.suy_ra` tính giai đoạn từ dữ liệu rồi đưa vào prompt như **thông tin**.
Mô hình không có trường nào để khai lại nó. Xem `contract.py`.
"""
import logging
import re
from typing import Any

from app.advisor import client, qa
from app.agent import contract, state
from app.consultation import context_builder, eligibility, lien_he, next_question
from app.memory import render as bo_nho_render
from app.db import session_memory


logger = logging.getLogger(__name__)

# Số lượt gần nhất mang theo. Cùng con số với phòng tư vấn theo đơn, cùng lý do:
# đủ để hiểu "còn cái kia thì sao", không đủ để một câu sai ở lượt hai sống sót
# thành sự thật ở lượt mười.
SO_LUOT_NHO = 3

# Ngưỡng chờ cho một lượt của Agent. Dài hơn ngưỡng chung 12 giây vì khối JSON
# sinh lâu hơn một câu trả lời thuần — xem chỗ gọi `sinh_van_ban` dưới đây.
#
# Không để vô hạn: ứng viên đang ngồi trước màn hình, và sau 25 giây thì câu trả
# lời đến cũng đã muộn. Quá ngưỡng thì rơi về "trợ lý đang bận", vẫn có đường đi
# tiếp bằng cách để lại tin nhắn cho nhân viên.
NGUONG_CHO_GIAY = 25.0

PROMPT = """Bạn là trợ lý tư vấn của một công ty tuyển dụng điều dưỡng đi Nhật Bản.
Bạn đang nói chuyện với một ứng viên về HỒ SƠ CỦA CHÍNH HỌ và kết quả đối chiếu
hồ sơ đó với các đơn tuyển dụng.

[Giai đoạn hiện tại của ứng viên]
{giai_doan}

[Hồ sơ ứng viên]
{ho_so}

[Kết quả đối chiếu]
{doi_chieu}

[Điều kiện mức nền của chương trình]
{dieu_kien_nen}

{bo_nho}[Những lượt gần đây]
{lich_su}

[Câu ứng viên vừa hỏi]
{cau_hoi}

QUY TẮC — vi phạm thì câu trả lời bị loại bỏ hoàn toàn:

1. Chỉ dùng thông tin trong các khối trên. Không có thì nói chưa có thông tin.
2. KHÔNG nêu con số nào không xuất hiện trong các khối trên. Không tự tính, không
   làm tròn, không quy đổi.
3. KHÔNG kết luận ứng viên đạt hay không đạt. Việc đó đã nằm trong khối đối chiếu,
   bạn chỉ diễn đạt lại.
4. KHÔNG hứa trúng tuyển, có visa, hay được xuất cảnh. KHÔNG cam kết thay công ty
   về bước tiếp theo.
5. Nói về điều kiện của đơn và của chương trình, không phán xét về con người.
6. Phân biệt rõ nguồn khi nhắc lại dữ liệu:
   - thứ CV ghi mà ứng viên chưa xác nhận: "CV đang ghi nhận..."
   - thứ nghe trong hội thoại: "bạn từng chia sẻ rằng..."
   - thứ ứng viên đã xác nhận: "bạn đã xác nhận..."
   - thứ hệ thống tính ra: "hệ thống đối chiếu cho thấy..."
7. Viết tiếng Việt, 2–4 câu, giọng thân thiện và gọi ứng viên là "bạn".
   Câu phải nói hết ý và kết thúc bằng dấu chấm.

TRẢ VỀ ĐÚNG MỘT KHỐI JSON, không bọc trong dấu nháy ba, không thêm chữ nào ngoài khối:

{{
  "reply": "câu trả lời gửi cho ứng viên",
  "intent": "ý định của lượt này, vài từ tiếng Việt",
  "facts_to_save": [
    {{"field": "tên trường", "value": giá trị, "evidence": "câu nguyên văn ứng viên đã nói"}}
  ],
  "next_best_action": {{"type": "ask_question|confirm_profile|view_order|handoff|none",
                        "label": "nhãn nút", "target": "mã đơn hoặc null"}},
  "handoff": {{"required": false, "reason": ""}}
}}

Về "facts_to_save":
- Chỉ đưa vào thứ **ứng viên vừa nói ra trong câu hỏi của họ**, không suy diễn,
  không lấy lại thứ đã có trong hồ sơ.
- Mỗi điều phải kèm "evidence" là câu nguyên văn của ứng viên.
- Không có gì mới thì để danh sách rỗng. Danh sách rỗng là câu trả lời tốt.
- Đây chỉ là **đề xuất**. Hệ thống sẽ hỏi lại ứng viên trước khi lưu, nên đừng
  nói với họ rằng hồ sơ đã được cập nhật.
"""


async def tra_loi(
    *,
    cau_hoi: str,
    profile: dict[str, Any] | None,
    trang_thai: state.TrangThai,
    khoi_doi_chieu: str,
    lich_su: list[dict[str, str]] | None = None,
    bo_nho: dict[str, Any] | None = None,
) -> tuple[contract.KetQua, str, str]:
    """Trả `(kết quả, nguồn, model)`.

    `nguồn` là một trong ba giá trị `qa.NGUON_*` — giữ đúng bộ ba đã dùng ở phòng
    tư vấn theo đơn, để giao diện và bảng thống kê không phải học thêm nhãn mới.

    Không bao giờ ném lỗi: mọi đường thất bại đều dẫn tới một câu có đường đi
    tiếp. Ứng viên đứng giữa một cuộc trò chuyện mà không nhận được gì là kết quả
    tệ nhất ở đây, tệ hơn cả một câu trả lời nghèo.
    """
    ho_so_text = context_builder.render(profile) if profile else ""
    dieu_kien = "\n\n".join((eligibility.render_muc_nen(), lien_he.render()))

    # Khối cho phép: đúng những gì chốt số được dùng để so.
    #
    # `bo_nho` CỐ Ý không nằm trong đó — nó chở chủ đề đã bàn và câu hỏi nguyên
    # văn của khách, không chở dữ liệu để trả lời, nên một con số lọt vào đó cũng
    # không được phép đi ra ngoài. Cùng quyết định với `qa.tra_loi`.
    #
    # Nhưng **câu khách vừa hỏi thì có**, và đó là khác biệt bắt buộc giữa đường
    # này với phòng tư vấn theo đơn.
    #
    # Lý do: việc chính của Agent là nghe khách nói ra một điều rồi nhắc lại để
    # xin xác nhận. Khách nói "em làm hai năm rồi", mô hình đáp "bạn có 2 năm
    # kinh nghiệm…" — số 2 không nằm trong hồ sơ hay kết quả đối chiếu, nên chốt
    # số loại cả câu. Đo trên mô hình thật ngày 02/10: đúng lượt đầu tiên đã bị
    # loại vì số `2`, và `facts_to_save` mất theo. Nghĩa là tính năng chính của
    # Agent gần như không bao giờ chạy được.
    #
    # Đây cũng là nguyên tắc khung chat đã chốt: **số nào khách vừa nhắc thì bot
    # được nhắc lại, số nào không thì không** (`conversation/response_validator`).
    # Nó không nới lá chắn: số mô hình tự nghĩ ra vẫn bị chặn như cũ.
    khoi_cho_phep = "\n".join(
        (ho_so_text, khoi_doi_chieu, dieu_kien, _so_khach_vua_noi(cau_hoi))
    )

    prompt = PROMPT.format(
        giai_doan=_mo_ta_giai_doan(trang_thai),
        ho_so=ho_so_text or "[Chưa biết gì về ứng viên này]",
        doi_chieu=khoi_doi_chieu or "(chưa đối chiếu)",
        dieu_kien_nen=dieu_kien,
        bo_nho=_khoi_bo_nho(bo_nho),
        lich_su=_lich_su(lich_su or []),
        cau_hoi=cau_hoi.strip(),
    )

    van_ban, ly_do_goi, model = await client.sinh_van_ban(
        prompt,
        temperature=0.3,
        max_tokens=1100,
        # Nới ngưỡng chờ riêng cho đường này.
        #
        # Lượt ở đây xin một khối JSON có `reply` cùng bốn trường nữa bên trong,
        # nên nó sinh dài hơn hẳn một câu trả lời thuần. Với ngưỡng chung 12 giây
        # thì nó timeout thường xuyên — đo thật ngày 02/10: hai lượt liền trả
        # `ReadTimeout` trong khi vẫn còn hạn mức.
        #
        # Không nâng ngưỡng chung: 12 giây là đúng cho phòng tư vấn theo đơn, và
        # nâng lên là bắt ứng viên ở đường ấy ngồi chờ lâu hơn mà không được gì.
        timeout=NGUONG_CHO_GIAY,
    )
    if van_ban is None:
        logger.warning("Agent tư vấn: không gọi được mô hình (%s).", ly_do_goi)
        return (
            contract.KetQua(reply=qa.CAU_KHONG_GOI_DUOC),
            qa.NGUON_KHONG_GOI_DUOC,
            model,
        )

    khoi = contract.doc_khoi_json(van_ban)
    if khoi is None:
        # Mô hình phớt lờ yêu cầu định dạng. Vẫn còn dùng được: lấy cả câu làm
        # `reply` rồi cho nó đi qua đúng bộ chốt như mọi lượt khác. Mất phần cấu
        # trúc, không mất lượt.
        logger.info("Agent tư vấn: không bóc được JSON, dùng cả câu làm reply.")
        khoi = {"reply": van_ban}

    reply = str(khoi.get("reply") or "").strip()
    ly_do_loai = qa.kiem_tra(reply, khoi_cho_phep)
    if ly_do_loai is not None:
        # Câu trả lời bị loại thì bỏ luôn phần cấu trúc. Hai phần đến từ cùng một
        # lượt sinh; tin phần này mà bỏ phần kia là không có căn cứ nào.
        logger.warning("Agent tư vấn: loại câu trả lời (%s).", ly_do_loai)
        return (
            contract.KetQua(reply=qa.CAU_KHONG_BIET, da_loai=(ly_do_loai,)),
            qa.NGUON_KHONG_BIET,
            model,
        )

    de_xuat, loai_de_xuat = contract.kiem_de_xuat(
        khoi.get("facts_to_save"), profile=profile
    )
    hanh_dong, loai_hd = contract.kiem_hanh_dong(khoi.get("next_best_action"))
    ban_giao_tho = khoi.get("handoff") if isinstance(khoi.get("handoff"), dict) else {}

    return (
        contract.KetQua(
            reply=reply,
            intent=str(khoi.get("intent") or "").strip()[:60],
            de_xuat=tuple(de_xuat),
            hanh_dong_goi_y=hanh_dong,
            can_nhan_vien=bool(ban_giao_tho.get("required")),
            ly_do_nhan_vien=str(ban_giao_tho.get("reason") or "").strip()[:300],
            da_loai=tuple(loai_de_xuat + loai_hd),
        ),
        qa.NGUON_MO_HINH,
        model,
    )


# Số đếm nhỏ viết bằng chữ. Khách gõ "hai năm", mô hình đáp "2 năm" — và đó là
# cách người ta nói, không phải lỗi của mô hình.
#
# Chỉ tới mười, và chỉ dùng để **mở rộng tập số cho phép** suy từ câu của khách.
# Không áp lên câu trả lời: áp lên đó là mở một hướng khác hẳn, vì nó sẽ biến
# những cụm như "một số đơn" thành con số 1 rồi đem đi so.
_SO_BANG_CHU: dict[str, str] = {
    "một": "1", "hai": "2", "ba": "3", "bốn": "4", "năm": "5",
    "sáu": "6", "bảy": "7", "tám": "8", "chín": "9", "mười": "10",
}
_TU_SO_CHU = re.compile(
    r"\b(" + "|".join(_SO_BANG_CHU) + r")\b", re.IGNORECASE
)


def _so_khach_vua_noi(cau_hoi: str) -> str:
    """Câu của khách, kèm bản đổi số viết bằng chữ sang chữ số.

    Trả về **văn bản** chứ không phải tập số, để nơi gọi ghép thẳng vào khối cho
    phép — chốt số tự bóc số ra khỏi đó bằng `phrasing.so_trong`.

    Giữ cả câu gốc: khách có thể gõ thẳng chữ số ("em làm 2 năm"), và khi ấy bản
    đổi không thêm gì nhưng câu gốc đã đủ.

    ## Chỗ này vẫn còn hở, nói rõ chứ không giả vờ đã kín

    Số viết bằng chữ trong **câu trả lời** thì chốt số không thấy: mô hình viết
    "hai trăm năm mươi triệu" là không có chữ số nào để bóc, nên nó đi qua. Đây
    là lỗ hổng có từ trước và không sửa ở đây — sửa đúng cần một bộ đọc số tiếng
    Việt ghép được ("hai trăm năm mươi"), và một bộ nửa vời sẽ chặn oan những cụm
    như "một số đơn" hay "năm nay".
    """
    if not cau_hoi:
        return ""
    doi = _TU_SO_CHU.sub(lambda m: _SO_BANG_CHU[m.group(1).lower()], cau_hoi)
    return f"{cau_hoi}\n{doi}" if doi != cau_hoi else cau_hoi


def _mo_ta_giai_doan(trang_thai: state.TrangThai) -> str:
    """Giai đoạn và việc còn thiếu, viết cho mô hình đọc.

    Đưa vào prompt như **thông tin đã biết**, không như câu hỏi. Mô hình cần biết
    ứng viên đang ở đâu để không gợi một bước họ đã làm xong — nhưng nó không có
    đường nào để đổi con số này.
    """
    dong = [
        f"- Giai đoạn: {state.NHAN.get(trang_thai.stage, trang_thai.stage)}",
        f"- Hồ sơ đã được ứng viên xác nhận: {'có' if trang_thai.da_xac_nhan else 'chưa'}",
    ]
    if trang_thai.so_don_dat is not None:
        dong.append(f"- Số đơn ứng viên đủ điều kiện nộp: {trang_thai.so_don_dat}")
    if trang_thai.don_dang_xet:
        dong.append(f"- Đơn ứng viên đang xem: {trang_thai.don_dang_xet}")
    if trang_thai.con_thieu:
        dong.append(f"- Hồ sơ còn thiếu: {', '.join(trang_thai.con_thieu)}")
    dong.append(
        f"- Việc hệ thống cho là nên làm tiếp: {trang_thai.hanh_dong.label}"
    )
    return "\n".join(dong)


def _khoi_bo_nho(bo_nho: dict[str, Any] | None) -> str:
    if not bo_nho:
        return ""
    khoi = bo_nho_render.render(bo_nho, cho=session_memory.BEN_TU_VAN)
    return f"{khoi}\n\n" if khoi.strip() else ""


def _lich_su(luot: list[dict[str, str]]) -> str:
    if not luot:
        return "(chưa có lượt nào)"
    dong = []
    for l in luot[-SO_LUOT_NHO:]:
        dong.append(f"Ứng viên: {l.get('question', '')}")
        dong.append(f"Trợ lý: {l.get('answer', '')}")
    return "\n".join(dong)


def cau_hoi_con_thieu(profile: dict[str, Any] | None) -> list[str]:
    """Một hoặc hai câu hỏi về dữ liệu còn thiếu, dựng bằng quy tắc.

    Mở ra ngoài để giao diện hiện thành nút bấm. Trước đây bộ câu này chỉ được
    nhét vào prompt của khung chat, nên giao diện không biết nó tồn tại và ứng
    viên không bao giờ thấy nó ở dạng bấm được.
    """
    return next_question.chon(profile)
