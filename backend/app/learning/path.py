"""Ghép lộ trình học từ trình độ hiện tại tới trình độ đơn yêu cầu.

Thuần: không đọc database, không đọc đồng hồ, không gọi mô hình ngôn ngữ. Nhận
vào danh sách khóa và hai mốc trình độ, trả về chuỗi khóa phải học cùng tổng thời
gian và tổng học phí. Nhờ vậy kiểm thử được tuyệt đối, và cùng dữ liệu vào thì
luôn cùng kết quả ra — giống bộ đối chiếu.

## Không có đường thì trả rỗng, không nội suy

Đây là điểm quan trọng nhất của module. Nếu danh mục không có khóa nào bắc được
từ trình độ hiện tại tới trình độ cần, hàm trả về `None` và phần tư vấn chỉ nói
định tính: *"bạn cần học thêm để đủ N4, nhân viên sẽ tư vấn khóa phù hợp"*.

Cái sai dễ mắc là đoán: thấy có khóa "chưa học → N4 mất 6 tháng" rồi suy ra
"N5 → N4 mất 3 tháng" vì N5 là nửa đường. Suy như vậy nghe hợp lý nhưng không có
gì đỡ lưng, và con số bịa ra sẽ được đọc cho một người đang tính chuyện vay tiền.

## Chọn đường ngắn nhất theo số tháng, phá thế hòa bằng mã khóa

Phải tất định. Hai đường cùng số tháng thì lấy đường có dãy mã khóa nhỏ hơn theo
thứ tự chữ, chứ không phụ thuộc thứ tự bản ghi trả về từ database.
"""
from dataclasses import dataclass, field
from typing import Any, Sequence

from app.matching.catalog import JAPANESE_LEVEL_LABELS, JAPANESE_RANK


# Chặn vòng lặp vô tận nếu ai đó khai một khóa "N4 → N4", và chặn cả lộ trình dài
# vô lý. Bốn chặng là đã đi từ chưa học lên N1.
MAX_CHANG = 4


@dataclass(frozen=True)
class LearningPath:
    """Một lộ trình đã ghép xong. Mọi con số đều cộng từ các khóa trong `courses`."""

    level_from: str
    level_to: str
    courses: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    months_min: int = 0
    months_max: int = 0
    tuition_vnd: int | None = None
    # Bật khi có khóa trong lộ trình thiếu học phí. Thiếu một mắt thì tổng không
    # còn là tổng — thà nói "chưa có đủ thông tin học phí" hơn là đưa số thiếu.
    tuition_incomplete: bool = False
    package_total_vnd: int | None = None

    @property
    def months_text(self) -> str:
        """Khoảng thời gian, viết đúng như nguồn chứ không làm tròn thành một số."""
        if self.months_max and self.months_max != self.months_min:
            return f"{self.months_min}–{self.months_max} tháng"
        return f"{self.months_min} tháng"


def _rank(level: str | None) -> int | None:
    if not level:
        return None
    return JAPANESE_RANK.get(level)


def label(level: str | None) -> str:
    """Nhãn tiếng Việt của một mốc trình độ. Mã lạ thì trả lại nguyên mã."""
    if not level:
        return "chưa rõ"
    return JAPANESE_LEVEL_LABELS.get(level, level)


def can_skip(level_from: str | None, level_to: str | None) -> bool:
    """Trình độ hiện tại đã bằng hoặc hơn mức cần — không phải học gì thêm."""
    hien_tai = _rank(level_from)
    can = _rank(level_to)
    if hien_tai is None or can is None:
        return False
    return hien_tai >= can


def build(
    courses: Sequence[dict[str, Any]],
    *,
    level_from: str | None,
    level_to: str | None,
) -> LearningPath | None:
    """Chuỗi khóa ngắn nhất bắc từ `level_from` tới `level_to`.

    Trả `None` trong ba trường hợp, và cả ba đều là "không biết" chứ không phải
    "không cần học":

    - Thiếu một trong hai mốc trình độ (hồ sơ chưa khai, hoặc đơn không ghi).
    - Mốc không có trong danh mục trình độ.
    - Danh mục khóa không có đường nào nối được hai mốc.

    Nơi gọi phải phân biệt `None` với `LearningPath` rỗng: `None` là chưa tính
    được, còn lộ trình 0 chặng thì dùng `can_skip` để biết trước.
    """
    bat_dau = _rank(level_from)
    dich = _rank(level_to)
    if bat_dau is None or dich is None or bat_dau >= dich:
        return None

    # Chỉ xét khóa nâng trình độ lên. Khóa khai ngược hoặc khai ngang là dữ liệu
    # hỏng; bỏ ở đây thay vì để nó tạo vòng lặp trong lúc tìm đường.
    hop_le = [
        khoa
        for khoa in courses
        if (_rank(khoa.get("level_from")) is not None
            and _rank(khoa.get("level_to")) is not None
            and _rank(khoa["level_from"]) < _rank(khoa["level_to"]))
    ]

    # Tìm rộng theo số chặng, mỗi mức sắp xếp tất định. Số khóa luôn nhỏ nên
    # không cần thuật toán phức tạp; đổi lại đọc là hiểu ngay nó chọn gì.
    tot_nhat: tuple[int, tuple[str, ...], list[dict[str, Any]]] | None = None
    hang_doi: list[tuple[int, list[dict[str, Any]]]] = [(bat_dau, [])]

    while hang_doi:
        moi: list[tuple[int, list[dict[str, Any]]]] = []
        for muc, duong in hang_doi:
            if len(duong) >= MAX_CHANG:
                continue
            tiep = sorted(
                (k for k in hop_le if _rank(k["level_from"]) == muc),
                key=lambda k: str(k.get("code") or ""),
            )
            for khoa in tiep:
                duong_moi = [*duong, khoa]
                muc_moi = _rank(khoa["level_to"])
                if muc_moi >= dich:
                    thang = sum(int(k.get("months_min") or 0) for k in duong_moi)
                    ma = tuple(str(k.get("code") or "") for k in duong_moi)
                    if tot_nhat is None or (thang, ma) < (tot_nhat[0], tot_nhat[1]):
                        tot_nhat = (thang, ma, duong_moi)
                    continue
                moi.append((muc_moi, duong_moi))
        # Đã tìm được đường ở mức chặng này thì không cần đi sâu hơn: thêm chặng
        # chỉ làm dài ra chứ không ngắn lại.
        if tot_nhat is not None:
            break
        hang_doi = moi

    if tot_nhat is None:
        return None

    duong = tot_nhat[2]
    hoc_phi = [k.get("tuition_vnd") for k in duong]
    thieu_hoc_phi = any(gia is None for gia in hoc_phi)

    return LearningPath(
        level_from=level_from,
        level_to=level_to,
        courses=tuple(duong),
        months_min=sum(int(k.get("months_min") or 0) for k in duong),
        months_max=sum(
            int(k.get("months_max") or k.get("months_min") or 0) for k in duong
        ),
        tuition_vnd=None if thieu_hoc_phi else sum(int(g) for g in hoc_phi),
        tuition_incomplete=thieu_hoc_phi,
        # Tổng gói lấy của khóa cuối: nó là chặng gắn với việc xuất cảnh, và tổng
        # gói là con số của cả chương trình chứ không phải cộng dồn từng khóa.
        package_total_vnd=duong[-1].get("package_total_vnd"),
    )
