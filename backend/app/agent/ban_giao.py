"""Bản tóm tắt bàn giao cho nhân viên — dựng bằng mã, không gọi mô hình.

## Vì sao không để mô hình viết bản này

Nhân viên đọc bản này rồi **gọi điện cho một người thật**. Mỗi dòng trong đó sẽ
được nói ra miệng, và nếu một dòng sai thì người nghe là ứng viên — họ sẽ sửa lại
nhân viên, và niềm tin vào cả hệ thống mất ngay trong cuộc gọi đó.

Nên bản này ghép từ dữ liệu có cấu trúc: hồ sơ, nhật ký đối chiếu, lượt hỏi đáp,
yêu cầu hỗ trợ. Mọi dòng truy ngược được về một bản ghi. Mô hình **không tham gia**
— khác với lời tư vấn gửi cho ứng viên, nơi mô hình được diễn đạt lại vì ứng viên
còn đọc được khối dữ liệu gốc ngay bên cạnh để đối chiếu.

Đây cũng là điều `docs/design/14 §2.2` đã chốt cho phiếu tóm tắt tư vấn, và bản
này đi theo cùng nguyên tắc.

## Tách rõ đã xác nhận với chưa xác nhận

Phần nguy hiểm nhất của một bản bàn giao là trộn hai thứ ấy. Nhân viên đọc một
dòng "N4" rồi gọi điện nói "bên em thấy chị có N4" — trong khi đó là thứ máy đọc
từ CV và chưa ai kiểm. Nếu máy đọc nhầm thì nhân viên vừa khẳng định một điều sai
thay cho công ty.

Nên hai khối riêng, có tiêu đề riêng, và khối chưa xác nhận ghi rõ nguồn từng dòng.

## Vì sao có "việc nhân viên nên làm tiếp"

Một bản tóm tắt chỉ kể tình hình thì người đọc vẫn phải tự nghĩ ra việc. Dòng
cuối nói thẳng việc nên làm, lấy từ `state.suy_ra` — cùng một hàm sinh ra nút
gợi ý cho ứng viên, nên hai bên không nói hai điều khác nhau.
"""
from typing import Any

from app.agent import state
from app.db import candidate_profiles as profiles


# Nguồn nào coi là đã được người xác nhận. `staff` đứng cùng `user_confirmed`:
# nhân viên chốt bằng tay thì cũng là một người đã kiểm.
NGUON_DA_XAC_NHAN = ("user_confirmed", "staff")

# Tiền tố của lượt Agent tự mở đầu. Một nguồn duy nhất với `api/agent.py` để hai
# nơi không bao giờ dùng hai tiền tố khác nhau — lệch một lần là nhãn nội bộ lọt
# ra bản nhân viên đọc.
NHAN_HE_THONG = "[hệ thống]"

NHAN_NGUON: dict[str, str] = {
    "cv": "đọc từ CV",
    "chat": "nghe trong hội thoại",
    "user_confirmed": "ứng viên xác nhận",
    "staff": "nhân viên cập nhật",
}

TEN_TRUONG: dict[str, str] = {
    "full_name": "Họ và tên",
    "birth_year": "Năm sinh",
    "gender": "Giới tính",
    "education_level": "Bằng cấp",
    "major": "Chuyên ngành",
    "japanese_level": "Tiếng Nhật",
    "experience_years": "Kinh nghiệm",
    "care_experience": "Từng chăm sóc người bệnh",
    "phone": "Điện thoại",
    "desired_prefecture": "Tỉnh mong muốn",
    "desired_region_group": "Vùng mong muốn",
    "desired_employer_type": "Loại cơ sở",
    "salary_expectation_jpy": "Lương mong muốn",
    "budget_vnd": "Ngân sách",
    "reason": "Lý do muốn đi",
    "notes": "Ghi chú",
}


def dung(
    *,
    profile: dict[str, Any] | None,
    trang_thai: state.TrangThai,
    log: dict[str, Any] | None = None,
    luot_hoi: list[dict[str, Any]] | None = None,
    loi_nhan: str = "",
    lich_hen: list[dict[str, Any]] | None = None,
) -> str:
    """Bản bàn giao dạng văn bản, in ra được và đọc trong vài chục giây.

    Thân bản **không có dòng tiêu đề**. Mọi nơi hiển thị nó đều đặt nó trong một
    khối đã có nhãn — hệ quản trị ghi "Tóm tắt bàn giao — đọc trước khi gọi",
    trang liên hệ ghi "Xem trước thứ nhân viên sẽ đọc". Thêm tiêu đề vào thân thì
    màn hình hiện hai dòng tiêu đề liền nhau; bắt được trên hệ quản trị thật
    ngày 01/10.
    """
    phan: list[str] = [
        f"TÌNH TRẠNG: {state.NHAN.get(trang_thai.stage, trang_thai.stage)}"
    ]

    phan.append(_khoi_da_xac_nhan(profile))
    phan.append(_khoi_chua_xac_nhan(profile))
    phan.append(_khoi_nguyen_vong(profile))
    phan.append(_khoi_doi_chieu(log, trang_thai))
    phan.append(_khoi_con_thieu(trang_thai))
    phan.append(_khoi_cau_hoi(luot_hoi or []))

    phan.append(_khoi_lich_hen(lich_hen or []))

    if loi_nhan.strip():
        phan.append(f"\nLỜI NHẮN RIÊNG CỦA ỨNG VIÊN\n  {loi_nhan.strip()}")

    phan.append(
        f"\nVIỆC NÊN LÀM TIẾP\n  {trang_thai.hanh_dong.label}"
        + (f" ({trang_thai.hanh_dong.target})" if trang_thai.hanh_dong.target else "")
    )
    phan.append(
        "\nBản này ghép từ dữ liệu đã lưu, không do mô hình ngôn ngữ viết.\n"
        "Mọi con số cần kiểm chứng lại khi gọi điện."
    )
    return "\n".join(p for p in phan if p)


def _o(profile: dict[str, Any] | None, key: str) -> dict[str, Any] | None:
    if not profile:
        return None
    for muc in ("fields", "preferences"):
        cell = (profile.get(muc) or {}).get(key)
        if isinstance(cell, dict) and cell.get("value") not in (None, ""):
            return cell
    return None


def _doc(profile: dict[str, Any], key: str, cell: dict[str, Any]) -> str:
    labels = profile.get("labels") or {}
    gia_tri = cell.get("value")
    if key == "care_experience":
        return "Có" if gia_tri else "Không"
    if key == "experience_years":
        so = int(gia_tri) if float(gia_tri).is_integer() else gia_tri
        return f"{so} năm"
    if key == "salary_expectation_jpy":
        return f"{int(gia_tri):,} yên/tháng".replace(",", ".")
    if key == "budget_vnd":
        return f"{int(gia_tri):,} đồng".replace(",", ".")
    return str(labels.get(key) or gia_tri)


def _khoi_da_xac_nhan(profile: dict[str, Any] | None) -> str:
    if not profile:
        return "\nỨNG VIÊN ĐÃ XÁC NHẬN\n  (chưa có hồ sơ)"
    profiles.decorate(profile)
    dong = [
        f"  {TEN_TRUONG.get(k, k)}: {_doc(profile, k, o)}"
        for k in profiles.FIELD_KEYS
        if (o := _o(profile, k)) and o.get("source") in NGUON_DA_XAC_NHAN
    ]
    dong.sort()
    return "\nỨNG VIÊN ĐÃ XÁC NHẬN\n" + ("\n".join(dong) or "  (chưa xác nhận mục nào)")


def _khoi_chua_xac_nhan(profile: dict[str, Any] | None) -> str:
    """Dữ liệu máy biết mà người chưa kiểm. Ghi rõ nguồn từng dòng.

    Khối này là lý do bản bàn giao tồn tại ở dạng hai khối thay vì một bảng. Nhân
    viên phải thấy được chỗ nào mình đang đọc một phỏng đoán của máy, để đừng
    khẳng định nó thay công ty trong cuộc gọi.
    """
    if not profile:
        return ""
    dong = [
        f"  {TEN_TRUONG.get(k, k)}: {_doc(profile, k, o)}  [{NHAN_NGUON.get(o.get('source', ''), o.get('source', ''))}]"
        for k in profiles.FIELD_KEYS
        if (o := _o(profile, k)) and o.get("source") not in NGUON_DA_XAC_NHAN
    ]
    if not dong:
        return ""
    dong.sort()
    return "\nMÁY ĐỌC ĐƯỢC, ỨNG VIÊN CHƯA XÁC NHẬN\n" + "\n".join(dong)


def _khoi_nguyen_vong(profile: dict[str, Any] | None) -> str:
    if not profile:
        return ""
    dong = [
        f"  {TEN_TRUONG.get(k, k)}: {_doc(profile, k, o)}"
        for k in profiles.PREFERENCE_KEYS
        if (o := _o(profile, k))
    ]
    if not dong:
        return "\nNGUYỆN VỌNG\n  (ứng viên chưa nêu)"
    dong.sort()
    return "\nNGUYỆN VỌNG\n" + "\n".join(dong)


def _khoi_doi_chieu(
    log: dict[str, Any] | None, trang_thai: state.TrangThai
) -> str:
    if log is None:
        return "\nĐỐI CHIẾU\n  Chưa đối chiếu lần nào."

    dat = [r for r in log.get("items") or () if r.get("eligible")]
    dong = [
        f"  Đã xét {log.get('total_considered') or len(log.get('items') or ())} đơn, "
        f"đủ điều kiện {len(dat)} đơn."
    ]
    for row in dat[:5]:
        sao = " ← đang xem" if row.get("code") == trang_thai.don_dang_xet else ""
        dong.append(
            f"    {row.get('code')} · {row.get('title')} · {row.get('score')}/100{sao}"
        )

    # Đơn bị loại: chỉ kể lý do, không kể tên hết. Nhân viên cần biết **vướng ở
    # đâu**, không cần đọc lại mười lăm dòng đơn đã trượt — bản đầy đủ vẫn nằm
    # trong nhật ký giới thiệu, bấm vào xem được.
    vuong = _dem_vuong(log)
    if vuong:
        dong.append("  Những tiêu chí làm trượt đơn:")
        dong.extend(f"    {ten}: {so} đơn" for ten, so in vuong)
    return "\nĐỐI CHIẾU\n" + "\n".join(dong)


def _dem_vuong(log: dict[str, Any]) -> list[tuple[str, int]]:
    from app.matching.engine import CHUA_RO, KHONG_DAT

    dem: dict[str, int] = {}
    for row in log.get("items") or ():
        if row.get("eligible"):
            continue
        for d in row.get("hard_rows") or ():
            if not isinstance(d, dict) or d.get("result") not in (KHONG_DAT, CHUA_RO):
                continue
            ten = str(d.get("label") or "").strip()
            if not ten:
                continue
            # Ghi rõ "chưa rõ" khác "không đạt": thiếu dữ liệu thì bổ sung là có
            # thể mở lại đơn, còn không đạt thật thì không.
            khoa = ten if d.get("result") == KHONG_DAT else f"{ten} (chưa rõ)"
            dem[khoa] = dem.get(khoa, 0) + 1
    return sorted(dem.items(), key=lambda c: (-c[1], c[0]))[:5]


def _khoi_con_thieu(trang_thai: state.TrangThai) -> str:
    if not trang_thai.con_thieu:
        return ""
    ten = [TEN_TRUONG.get(k, k) for k in trang_thai.con_thieu]
    return "\nTHÔNG TIN CÒN THIẾU\n  " + ", ".join(ten)


def _khoi_lich_hen(lich: list[dict[str, Any]]) -> str:
    """Lịch hẹn khách đã chọn.

    Đây là thứ duy nhất trong bản bàn giao có **mốc thời gian**, nên nó quyết
    định thứ tự việc trong ngày của nhân viên. Một bản đầy đủ mà không nói "khách
    hẹn 9h30 sáng mai" thì đọc xong vẫn phải mở màn hình khác để biết có phải gọi
    ngay không.

    Rỗng là chuyện thường: khách chưa biết lịch mình thì gửi yêu cầu trống và
    nhân viên hẹn lại. Khi ấy khối này không hiện gì, thay vì một tiêu đề trống.
    """
    if not lich:
        return ""
    from app.consultation import lich_hen as mo_dun

    dong = [f"  {mo_dun.mo_ta(l)}  [{l.get('status') or 'pending'}]" for l in lich]
    return "\nKHÁCH ĐÃ CHỌN KHUNG GIỜ\n" + "\n".join(dong)


def _khoi_cau_hoi(luot: list[dict[str, Any]]) -> str:
    """Những câu ứng viên đã hỏi, và chỗ nào trợ lý không trả lời được.

    Phần thứ hai quan trọng hơn phần thứ nhất: một câu trợ lý từ chối đoán là một
    câu **đang chờ người thật trả lời**, và nó phải nổi lên trong bản bàn giao
    chứ không nằm lẫn giữa những câu đã xong.
    """
    if not luot:
        return ""
    dong: list[str] = []
    chua_tra_loi: list[str] = []
    for l in luot[-8:]:
        cau = str(l.get("question") or "").strip()
        if not cau:
            continue
        # Bỏ lượt Agent tự mở đầu. Chúng được lưu với "câu hỏi" là một nhãn nội
        # bộ (`[hệ thống] sau_cv`), và ứng viên không hỏi câu đó.
        #
        # Bắt được trên trình duyệt thật 01/10: bản bàn giao in ra hai dòng
        # "- [hệ thống] sau_cv" và "- [hệ thống] sau_matching" dưới tiêu đề ỨNG
        # VIÊN ĐÃ HỎI. Giao diện phía khách đã ẩn chúng, nhưng bản bàn giao đi
        # một đường khác — nên nhân viên là người duy nhất phải đọc hai dòng vô
        # nghĩa, và họ không có cách nào biết đó là nhãn nội bộ.
        if cau.startswith(NHAN_HE_THONG):
            continue
        don = l.get("job_order_code")
        dong.append(f"  - {cau}" + (f"  (về đơn {don})" if don else ""))
        if l.get("source") in ("khong_biet", "khong_goi_duoc"):
            chua_tra_loi.append(cau)

    ra = "\nỨNG VIÊN ĐÃ HỎI\n" + "\n".join(dong)
    if chua_tra_loi:
        ra += "\n\n  TRỢ LÝ CHƯA TRẢ LỜI ĐƯỢC — cần nhân viên:\n"
        ra += "\n".join(f"    - {c}" for c in chua_tra_loi)
    return ra
