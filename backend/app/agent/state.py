"""Giai đoạn của ứng viên — suy từ dữ liệu, không hỏi mô hình.

## Vì sao không để mô hình tự khai giai đoạn

Bản thiết kế ban đầu cho mô hình trả về `current_stage` trong khối JSON của nó.
Nghe tiện, nhưng trạng thái **đã nằm sẵn trong dữ liệu**: hồ sơ có chưa, đã xác
nhận chưa, đã đối chiếu lần nào chưa, đang mở yêu cầu hỗ trợ nào. Hỏi mô hình một
thứ đã biết chắc là mở đường cho nó trả lời khác.

Và khi nó trả lời khác thì không có gì bắt được: giao diện nhảy sang bước khách
chưa tới, hoặc tụt về bước khách vừa làm xong. Không ngoại lệ nào, không log nào,
chỉ là một màn hình sai.

Module này thuần: không I/O, không gọi mô hình, nhận vào những gì đã đọc sẵn.
Nhờ vậy kiểm thử được tuyệt đối — và sáu giai đoạn dưới đây có đúng sáu bộ dữ
liệu vào sinh ra chúng.

## Sáu giai đoạn, và thứ tự không đảo được

Mỗi giai đoạn là đầu vào của giai đoạn sau. Không thể đối chiếu trước khi có hồ
sơ, không thể đăng ký trước khi đối chiếu.

Ngoại lệ duy nhất là `human_support`: nó **cắt ngang** bất cứ lúc nào, vì khách
có quyền xin gặp người thật ở mọi bước — kể cả ngay lúc vừa vào, và nhất là lúc
vừa bị báo chưa đủ điều kiện.
"""
from dataclasses import dataclass, field
from typing import Any


# Sáu giai đoạn. Chuỗi ký tự giữ nguyên trong API, nên đổi là đổi hợp đồng.
INTAKE = "intake"
PROFILE_REVIEW = "profile_review"
MATCHING = "matching"
ORDER_CONSULTATION = "order_consultation"
REGISTRATION = "registration"
HUMAN_SUPPORT = "human_support"

GIAI_DOAN = (
    INTAKE,
    PROFILE_REVIEW,
    MATCHING,
    ORDER_CONSULTATION,
    REGISTRATION,
    HUMAN_SUPPORT,
)

# Nhãn tiếng Việt cho giao diện. Để ở đây để chỉ có một bản dịch, không phải hai.
NHAN: dict[str, str] = {
    INTAKE: "Đang thu thập hồ sơ",
    PROFILE_REVIEW: "Chờ bạn xem lại và xác nhận",
    MATCHING: "Đã đối chiếu với các đơn",
    ORDER_CONSULTATION: "Đang tìm hiểu một đơn cụ thể",
    REGISTRATION: "Đã đăng ký, chờ nhân viên liên hệ",
    HUMAN_SUPPORT: "Đang chờ nhân viên trả lời",
}

# Hành động tiếp theo. Giao diện dựng nút từ đây, không tự nghĩ ra nút.
HD_HOI = "ask_question"
HD_XAC_NHAN = "confirm_profile"
HD_DOI_CHIEU = "run_matching"
HD_XEM_DON = "view_order"
HD_DANG_KY = "register"
HD_NHAN_VIEN = "handoff"
HD_KHONG = "none"


@dataclass(frozen=True)
class HanhDong:
    """Việc nên làm tiếp. `target` là mã đơn khi hành động cần một đơn."""

    type: str
    label: str
    target: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {"type": self.type, "label": self.label, "target": self.target}


@dataclass(frozen=True)
class TrangThai:
    stage: str
    # Trường đã biết và trường còn thiếu — tách ra vì Agent cần cả hai: biết rồi
    # thì đừng hỏi lại, còn thiếu thì mới là thứ đáng hỏi.
    da_biet: tuple[str, ...] = ()
    con_thieu: tuple[str, ...] = ()
    da_xac_nhan: bool = False
    so_don_dat: int | None = None
    don_dang_xet: str | None = None
    # Đơn đã đăng ký. Khác `don_dang_xet`: một cái là đang xem, một cái là đã chốt.
    don_da_dang_ky: tuple[str, ...] = ()
    yeu_cau_dang_mo: tuple[str, ...] = ()
    hanh_dong: HanhDong = field(
        default_factory=lambda: HanhDong(HD_KHONG, "Không có việc gì cần làm thêm")
    )

    def as_dict(self) -> dict[str, Any]:
        return {
            "current_stage": self.stage,
            "stage_label": NHAN.get(self.stage, self.stage),
            "known_fields": list(self.da_biet),
            "missing_information": list(self.con_thieu),
            "profile_confirmed": self.da_xac_nhan,
            "eligible_count": self.so_don_dat,
            "interested_order_codes": [self.don_dang_xet] if self.don_dang_xet else [],
            "registered_order_codes": list(self.don_da_dang_ky),
            "open_support_requests": list(self.yeu_cau_dang_mo),
            "next_best_action": self.hanh_dong.as_dict(),
        }


def suy_ra(
    *,
    profile: dict[str, Any] | None,
    log: dict[str, Any] | None = None,
    don_dang_xet: str | None = None,
    don_da_dang_ky: tuple[str, ...] = (),
    yeu_cau_dang_mo: tuple[str, ...] = (),
) -> TrangThai:
    """Giai đoạn hiện tại và việc nên làm tiếp.

    Thứ tự xét đi **từ cuối chuỗi về đầu**, không phải từ đầu về cuối. Người đã
    đăng ký thì vẫn còn thiếu dữ liệu nguyện vọng, và xét từ đầu sẽ kéo họ về lại
    bước khai hồ sơ — một màn hình nói "bạn chưa khai gì" với người vừa đăng ký
    xong là thứ không ai tha thứ.

    `yeu_cau_dang_mo` được xét trước tất cả: khách đã xin gặp người thật thì việc
    tiếp theo không phải là bấm thêm nút nào, mà là chờ.
    """
    from app.consultation.context_builder import con_thieu as tim_con_thieu

    co_ho_so = profile is not None
    da_xac_nhan = bool(profile) and profile.get("status") == "confirmed"
    thieu = tuple(tim_con_thieu(profile)) if profile else ()
    biet = tuple(_da_biet(profile)) if profile else ()
    so_dat = _dem_don_dat(log)

    # --- Giai đoạn ---
    if yeu_cau_dang_mo:
        stage = HUMAN_SUPPORT
    elif don_da_dang_ky:
        stage = REGISTRATION
    elif don_dang_xet:
        stage = ORDER_CONSULTATION
    elif so_dat is not None:
        stage = MATCHING
    elif co_ho_so and not da_xac_nhan:
        stage = PROFILE_REVIEW
    elif co_ho_so:
        # Hồ sơ đã xác nhận nhưng chưa đối chiếu lần nào — vẫn là bước chờ đối
        # chiếu, không phải bước xem lại.
        stage = MATCHING
    else:
        stage = INTAKE

    return TrangThai(
        stage=stage,
        da_biet=biet,
        con_thieu=thieu,
        da_xac_nhan=da_xac_nhan,
        so_don_dat=so_dat,
        don_dang_xet=don_dang_xet,
        don_da_dang_ky=don_da_dang_ky,
        yeu_cau_dang_mo=yeu_cau_dang_mo,
        hanh_dong=_hanh_dong(
            stage=stage,
            co_ho_so=co_ho_so,
            da_xac_nhan=da_xac_nhan,
            thieu=thieu,
            so_dat=so_dat,
            don_dang_xet=don_dang_xet,
            log=log,
        ),
    )


def _da_biet(profile: dict[str, Any]) -> list[str]:
    """Những trường đã có giá trị, bất kể nguồn nào.

    Gồm cả trường đọc từ CV mà khách chưa xác nhận: Agent **đã biết** nó, chỉ là
    chưa được coi là chắc. Hai chuyện khác nhau, và trộn chúng lại thì Agent sẽ
    hỏi lại đúng thứ vừa đọc được từ CV — việc khiến người ta nghĩ máy không đọc
    được gì cả.
    """
    ra: list[str] = []
    for muc in ("fields", "preferences"):
        for key, cell in (profile.get(muc) or {}).items():
            if isinstance(cell, dict) and cell.get("value") not in (None, ""):
                ra.append(key)
    return sorted(ra)


def _dem_don_dat(log: dict[str, Any] | None) -> int | None:
    """Số đơn đạt điều kiện, hoặc `None` khi **chưa đối chiếu lần nào**.

    Phân biệt `None` với `0` là quan trọng: chưa đối chiếu và đối chiếu ra không
    đơn nào là hai tình huống cần hai câu nói khác nhau. Gộp chúng thành `0` thì
    Agent sẽ báo "không có đơn nào phù hợp" với người chưa từng đối chiếu.
    """
    if log is None:
        return None
    so = log.get("eligible_count")
    if isinstance(so, int):
        return so
    return sum(1 for row in log.get("items") or () if row.get("eligible"))


def _hanh_dong(
    *,
    stage: str,
    co_ho_so: bool,
    da_xac_nhan: bool,
    thieu: tuple[str, ...],
    so_dat: int | None,
    don_dang_xet: str | None,
    log: dict[str, Any] | None,
) -> HanhDong:
    """Một việc, không phải một danh sách.

    Giao diện hiện nhiều nút thì người dùng phải chọn; Agent gợi **một** việc
    đáng làm nhất, và những nút khác vẫn nằm đó cho ai muốn đi đường khác.
    """
    if stage == HUMAN_SUPPORT:
        return HanhDong(HD_KHONG, "Nhân viên sẽ liên hệ trong giờ làm việc")

    if not co_ho_so:
        return HanhDong(HD_HOI, "Gửi CV hoặc khai nhanh vài mục")

    if not da_xac_nhan:
        return HanhDong(HD_XAC_NHAN, "Xem lại và xác nhận hồ sơ")

    if so_dat is None:
        return HanhDong(HD_DOI_CHIEU, "Đối chiếu hồ sơ với các đơn")

    if so_dat == 0:
        # Không đơn nào đạt. Thiếu dữ liệu thì bổ sung còn có cơ hội đổi kết quả;
        # đã đủ dữ liệu mà vẫn không đạt thì việc tiếp theo là gặp người thật,
        # không phải bấm đối chiếu lại cho ra cùng một kết quả.
        if thieu:
            return HanhDong(HD_HOI, "Bổ sung hồ sơ để mở thêm đơn")
        return HanhDong(HD_NHAN_VIEN, "Nhờ nhân viên tư vấn hướng khác")

    if don_dang_xet:
        return HanhDong(HD_DANG_KY, "Đăng ký đơn này", don_dang_xet)

    # Còn thiếu dữ liệu thì bổ sung trước khi chốt đơn: kết quả đang xếp hạng
    # trên dữ liệu khuyết, và một trường thiếu có thể đổi cả thứ tự.
    if thieu:
        return HanhDong(HD_HOI, "Bổ sung hồ sơ cho kết quả chắc hơn")

    tot_nhat = _don_tot_nhat(log)
    if tot_nhat:
        return HanhDong(HD_XEM_DON, "Xem đơn phù hợp nhất", tot_nhat)
    return HanhDong(HD_KHONG, "Bạn xem danh sách đơn phù hợp nhé")


def _don_tot_nhat(log: dict[str, Any] | None) -> str | None:
    """Mã đơn hạng 1 trong lần đối chiếu gần nhất, nếu nó đạt điều kiện."""
    for row in (log or {}).get("items") or ():
        if row.get("eligible") and row.get("rank") == 1:
            return row.get("code")
    return None
