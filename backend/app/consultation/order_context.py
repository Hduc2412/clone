"""Khối chữ mô tả đơn khách đang xét.

Cùng nguyên tắc với `context_builder.py`: thuần, không gọi mô hình, chỉ đọc bản
ghi đơn rồi dựng thành chữ để đưa vào ngữ cảnh.

## Vì sao tách riêng thay vì đưa cả bản ghi đơn cho mô hình

Bản ghi đơn có những trường **không phải việc của ứng viên**: ghi chú nội bộ, ai
tạo, đã tuyển được bao nhiêu người. Ném nguyên cả bản ghi vào câu lệnh là mở đúng
cánh cửa để một ngày nào đó bot đọc ra một con số nội bộ.

Nên ở đây là danh sách cho phép: chỉ những trường đã có trên trang công khai của
đơn mới được đưa vào. Thêm một trường nội bộ vào bản ghi sau này cũng không lọt.

## Tách điều kiện bắt buộc khỏi thông tin tham khảo

Hai nhóm có ý nghĩa khác hẳn nhau và bot phải nói khác nhau về chúng: thiếu một
điều kiện bắt buộc là không đi được, còn lương thấp hơn mong muốn chỉ là kém hợp
chứ không loại ai. Trộn hai nhóm vào một danh sách là mời bot nói "bạn chưa đạt
mức lương mong muốn" như thể đó là một tiêu chí trượt.

## Hai con số "tổng chi phí" và chỗ chúng va nhau

Đo trên máy thật ngày 25/09: ứng viên hỏi *"em cần chuẩn bị tổng cộng bao nhiêu
tiền"*, bot trả lời *"tổng chi phí chương trình là 110.000.000đ, **trong đó** học
phí tiếng Nhật là 35.000.000đ"*.

Cả hai con số đều có thật, nên chốt số cho qua — nó kiểm số **có tồn tại**, không
kiểm **quan hệ giữa các số**. Nhưng chữ *"trong đó"* là bot tự suy: 110 triệu là
chi phí ước tính của riêng đơn này, còn 35 triệu thuộc gói 90 triệu trong bảng
khóa học. Không ai biết 110 triệu ấy có bao gồm học phí hay không.

Nên hai nhãn phải gọi đúng tên từng con số, và khối này nói thẳng rằng quan hệ
giữa chúng là **chưa rõ**. Một câu "chưa rõ" nằm sẵn trong dữ liệu ngăn được suy
diễn tốt hơn mọi lời dặn trong câu lệnh.
"""
from datetime import date
from typing import Any

from app.matching import catalog


def _ngay(gia_tri: Any) -> str | None:
    """Ngày viết theo lối người Việt đọc, không phải lối máy lưu.

    Đơn lưu hạn nộp dạng chuỗi `2026-11-30`, còn thẻ đơn trên website in
    `30/11/2026`. Đưa dạng máy vào ngữ cảnh thì bot sẽ đọc lại đúng dạng ấy cho
    ứng viên, và hai con số cùng chỉ một ngày nằm cạnh nhau trên màn hình —
    người đọc phải dừng lại kiểm xem có phải cùng một ngày không.
    """
    if not gia_tri:
        return None
    if isinstance(gia_tri, date):
        return gia_tri.strftime("%d/%m/%Y")
    chuoi = str(gia_tri)
    try:
        return date.fromisoformat(chuoi[:10]).strftime("%d/%m/%Y")
    except ValueError:
        return chuoi


def _tien_yen(gia_tri: Any) -> str | None:
    if not gia_tri:
        return None
    return f"{int(gia_tri):,} yên".replace(",", ".")


def _tien_vnd(gia_tri: Any) -> str | None:
    if not gia_tri:
        return None
    return f"{int(gia_tri):,}đ".replace(",", ".")


def _dong_nhan_dien(order: dict[str, Any]) -> list[str]:
    dong = [f"Mã đơn: {order.get('code')}", f"Tên đơn: {order.get('title')}"]
    if order.get("employer_name"):
        dong.append(f"Cơ sở tiếp nhận: {order['employer_name']}")
    tinh = catalog.prefecture_label(order.get("prefecture"))
    if tinh:
        dong.append(f"Nơi làm việc: {tinh}")
    loai = catalog.EMPLOYER_TYPE_LABELS.get(order.get("employer_type") or "")
    if loai:
        dong.append(f"Loại hình cơ sở: {loai}")
    dien = catalog.PROGRAM_LABELS.get(order.get("program") or "")
    if dien:
        dong.append(f"Diện chương trình: {dien}")
    return dong


def _dong_bat_buoc(order: dict[str, Any]) -> list[str]:
    yeu_cau = order.get("requirements") or {}
    dong: list[str] = []

    han = order.get("deadline")
    if han:
        dong.append(f"Hạn nộp hồ sơ: {_ngay(han)}")

    tieng = yeu_cau.get("japanese_required")
    dong.append(
        f"Tiếng Nhật: {catalog.JAPANESE_LEVEL_LABELS.get(tieng, tieng)}"
        if tieng
        else "Tiếng Nhật: không yêu cầu"
    )

    bang = yeu_cau.get("education_required")
    dong.append(
        f"Bằng cấp: {catalog.EDUCATION_LABELS.get(bang, bang)} trở lên"
        if bang
        else "Bằng cấp: không yêu cầu"
    )

    kinh_nghiem = yeu_cau.get("experience_min")
    dong.append(
        f"Kinh nghiệm: từ {kinh_nghiem} năm" if kinh_nghiem else "Kinh nghiệm: không yêu cầu"
    )

    tuoi_min, tuoi_max = yeu_cau.get("age_min"), yeu_cau.get("age_max")
    if tuoi_min and tuoi_max:
        dong.append(f"Độ tuổi: {tuoi_min} đến {tuoi_max} tuổi")
    elif tuoi_min:
        dong.append(f"Độ tuổi: từ {tuoi_min} tuổi")
    elif tuoi_max:
        dong.append(f"Độ tuổi: đến {tuoi_max} tuổi")

    gioi = yeu_cau.get("gender_pref")
    dong.append(
        f"Giới tính: {catalog.GENDER_LABELS.get(gioi, gioi)}"
        if gioi
        else "Giới tính: không yêu cầu"
    )
    return dong


def _dong_tham_khao(order: dict[str, Any]) -> tuple[list[str], bool]:
    """Trả `(các dòng, có nêu chi phí của đơn không)`.

    Cần biết có nêu chi phí hay không để `render` quyết định có thêm câu cảnh báo
    về hai con số tổng hay không — thêm câu đó khi đơn không nói gì về chi phí
    chỉ làm khối dài ra mà không ngăn được gì.
    """
    ref = order.get("reference") or {}
    dong: list[str] = []

    luong_min = _tien_yen(ref.get("salary_min"))
    luong_max = _tien_yen(ref.get("salary_max"))
    if luong_min and luong_max:
        dong.append(f"Lương cơ bản: {luong_min} đến {luong_max} mỗi tháng")
    elif luong_min:
        dong.append(f"Lương cơ bản: từ {luong_min} mỗi tháng")

    chi_phi = _tien_vnd(ref.get("cost_total_vnd"))
    if chi_phi:
        # Nhãn phải nói rõ đây là chi phí **của riêng đơn này**, không phải một
        # con số tổng dùng chung. Nhãn cũ chỉ ghi "Tổng chi phí" và bot đem nó
        # gộp với học phí khóa tiếng Nhật.
        dong.append(f"Chi phí ước tính của riêng đơn này: {chi_phi}")

    for khoa, nhan in (("interview_date", "Ngày phỏng vấn"),
                       ("departure_expected", "Dự kiến xuất cảnh")):
        gia_tri = ref.get(khoa)
        if gia_tri:
            dong.append(f"{nhan}: {_ngay(gia_tri)}")

    phu_cap = ref.get("allowances") or ()
    if phu_cap:
        dong.append(f"Phụ cấp: {', '.join(str(p) for p in phu_cap)}")

    diem_manh = ref.get("highlights") or ()
    if diem_manh:
        dong.append(f"Điểm đáng chú ý: {'; '.join(str(d) for d in diem_manh)}")
    return dong, bool(chi_phi)


def render(order: dict[str, Any] | None) -> str:
    """Khối chữ về đơn. Rỗng khi không có đơn nào đang xét."""
    if not order:
        return ""

    phan = ["[Đơn khách đang xét]", *_dong_nhan_dien(order), ""]
    phan.append("Điều kiện bắt buộc — thiếu một mục là không nộp được đơn này:")
    phan += [f"- {d}" for d in _dong_bat_buoc(order)]

    tham_khao, co_chi_phi = _dong_tham_khao(order)
    if tham_khao:
        phan.append("")
        phan.append(
            "Thông tin tham khảo — KHÔNG phải điều kiện, không mục nào trong đây "
            "làm ứng viên bị loại:"
        )
        phan += [f"- {d}" for d in tham_khao]

    if co_chi_phi:
        phan.append("")
        phan.append(
            "LƯU Ý VỀ CHI PHÍ: chi phí ước tính của đơn này và học phí khóa tiếng "
            "Nhật là hai con số từ hai nguồn khác nhau. **Chưa rõ** chi phí của "
            "đơn đã bao gồm học phí hay chưa. Không được nói con số này nằm trong "
            "con số kia, không được cộng hay trừ chúng với nhau. Khách hỏi tổng "
            "tiền phải chuẩn bị thì nêu từng con số kèm đúng tên của nó, và nói "
            "nhân viên tư vấn sẽ báo con số cuối cùng."
        )

    phan.append("")
    phan.append(
        "Chỉ nói về đơn này bằng những dòng trên. Không suy ra điều kiện nào "
        "không có ở đây, và không so sánh với đơn khác."
    )
    return "\n".join(phan)
