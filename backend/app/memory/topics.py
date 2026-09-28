"""Gán chủ đề cho một câu hỏi — bằng từ khóa, không bằng mô hình.

Bộ nhớ chung cần biết khách đang lo về cái gì, nhưng **không được tốn thêm một
lượt gọi mô hình** cho việc ấy. Hạn mức gói miễn phí là 20 lượt mỗi ngày cho mỗi
model; tiêu một lượt để dán nhãn cho câu hỏi là tiêu vào phần không ai đọc, và
đúng lúc hạn mức cạn thì bộ nhớ chết trước cả con bot.

Nên ở đây là luật từ khóa thuần. Đổi lại:

- **Tất định.** Cùng câu hỏi luôn ra cùng nhãn, kiểm thử được tuyệt đối.
- **Chạy khi mất mạng.** Bộ nhớ vẫn hoạt động lúc mô hình chết.
- **Giải trình được.** Hội đồng hỏi "vì sao câu này được xếp vào chi phí" thì mở
  ra thấy đúng một dòng từ khóa, không phải một hộp đen.

Cái giá phải trả là nó bỏ sót những câu hỏi vòng vo. Chấp nhận được: bỏ sót một
nhãn chỉ làm bộ nhớ nghèo đi, còn gán sai một nhãn thì làm bên kia tưởng đã bàn
rồi và bỏ qua thứ khách đang thật sự lo.

Vì vậy luật ở đây **thiên về bỏ sót**: không khớp từ khóa nào thì trả `None` chứ
không đoán một chủ đề gần đúng.
"""
import re
import unicodedata


# Nhãn chủ đề. Giữ ít và rộng — đây là để hai bên biết "đã bàn tới chưa", không
# phải để phân loại tinh vi. Nhãn càng nhiều thì càng dễ có hai nhãn cùng nói về
# một nỗi lo, và lúc đó bộ nhớ báo "chưa bàn" trong khi đã bàn rồi.
CHI_PHI = "chi_phi"
TIENG_NHAT = "tieng_nhat"
SUC_KHOE = "suc_khoe"
TUOI = "tuoi"
BANG_CAP = "bang_cap"
LUONG = "luong"
THOI_GIAN = "thoi_gian"
CONG_VIEC = "cong_viec"
THU_TUC = "thu_tuc"
NHAN_VIEN = "nhan_vien"

NHAN = {
    CHI_PHI: "chi phí",
    TIENG_NHAT: "tiếng Nhật và việc học",
    SUC_KHOE: "sức khỏe và khám sức khỏe",
    TUOI: "độ tuổi",
    BANG_CAP: "bằng cấp",
    LUONG: "lương và thu nhập",
    THOI_GIAN: "thời gian, lịch trình, ngày bay",
    CONG_VIEC: "công việc phải làm",
    THU_TUC: "hồ sơ, thủ tục, giấy tờ",
    NHAN_VIEN: "gặp hoặc liên hệ nhân viên",
}

# Thứ tự có ý nghĩa: luật đứng trước thắng. "học phí bao nhiêu" phải ra `chi_phi`
# chứ không ra `tieng_nhat`, vì thứ khách đang hỏi là tiền.
_LUAT: tuple[tuple[str, str], ...] = (
    (CHI_PHI, r"chi phi|hoc phi|bao nhieu tien|het bao nhieu|dong bao nhieu|"
              r"phi|tien coc|dat coc|tra gop|vay von|tong goi|mat bao nhieu"),
    (LUONG, r"luong|thu nhap|kiem duoc|tang ca|phu cap|tro cap|yen mot thang"),
    (TIENG_NHAT, r"tieng nhat|tieng nhan|jlpt|\bn[1-5]\b|hoc tieng|khoa hoc|"
                 r"so cap|trinh do tieng"),
    (SUC_KHOE, r"suc khoe|kham|benh|viem gan|hiv|lao|can thi|chieu cao|can nang|"
               r"hinh xam|xam minh"),
    (TUOI, r"bao nhieu tuoi|do tuoi|gioi han tuoi|tuoi nao|qua tuoi|sinh nam"),
    (BANG_CAP, r"bang cap|bang dai hoc|bang cao dang|trung cap|tot nghiep|"
               r"chung chi hanh nghe|dieu duong vien"),
    (THOI_GIAN, r"bao lau|may thang|khi nao|thoi gian|ngay bay|xuat canh|"
                r"phong van khi nao|han nop"),
    (CONG_VIEC, r"cong viec|lam gi|nhiem vu|cham soc|vien duong lao|benh vien|"
                r"ca dem|gio lam"),
    (THU_TUC, r"ho so|thu tuc|giay to|visa|ho chieu|dang ky|nop don|ly lich"),
    (NHAN_VIEN, r"gap nhan vien|lien he|so dien thoai|tu van vien|hen gap|"
                r"goi dien|nhan vien tu van|gio lam viec"),
)


def _bo_dau(text: str) -> str:
    """Bỏ dấu tiếng Việt và hạ chữ thường.

    Người dùng gõ trên điện thoại rất hay bỏ dấu ("hoc phi bao nhieu"), nên luật
    từ khóa phải so trên bản không dấu, không thì nó chỉ bắt được một nửa.
    """
    tach = unicodedata.normalize("NFD", text.casefold())
    khong_dau = "".join(c for c in tach if unicodedata.category(c) != "Mn")
    # `đ` không phải là `d` cộng dấu nên bước trên không đụng tới nó.
    return khong_dau.replace("đ", "d").replace("Đ", "d")


def phan_loai(cau_hoi: str) -> str | None:
    """Trả nhãn chủ đề, hoặc `None` khi không chắc.

    `None` là câu trả lời hợp lệ và hay gặp. Xem docstring đầu file: thà bỏ sót
    còn hơn gán sai.
    """
    if not cau_hoi or not cau_hoi.strip():
        return None
    phang = _bo_dau(cau_hoi)
    for chu_de, mau in _LUAT:
        if re.search(mau, phang):
            return chu_de
    return None


def nhan_cua(chu_de: str) -> str:
    """Nhãn tiếng Việt để đưa vào khối chữ cho mô hình đọc."""
    return NHAN.get(chu_de, chu_de)
