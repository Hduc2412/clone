"""Không để số điện thoại thật lọt vào kho mã.

Kho mã này công khai. Số hotline của công ty là số của một người thật, và địa chỉ
văn phòng là địa điểm thật. Hai thứ đó không có lý do gì phải nằm trong nguồn:
chúng là **cấu hình của một lần triển khai**, không phải logic của hệ thống.

## Vì sao phải có ca kiểm thử, không chỉ dặn nhau

Ngày 29/09/2026 tôi rút số hotline khỏi kho mã. Trước đó nó nằm ở **bảy chỗ**, và
bốn trong số đó không ai nghĩ tới khi đi tìm:

- mặc định của `support_phone` trong `config.py` — chỗ duy nhất ai cũng nhớ
- `backend/.env.example`, và `README.md` chép lại cùng khối đó
- một biểu thức chính quy trong `ingestion/clean_knowledge.py` để sửa lỗi nhận
  dạng ảnh — cần biết số thật mới sửa được
- `placeholder` của ô nhập số điện thoại **của khách** trong giao diện tư vấn
  (vừa là chỗ lọt, vừa là lỗi giao diện: gợi ý cho khách chính số của công ty)
- ba tệp dữ liệu kiểm thử và hai bảng trong tài liệu
- và nặng nhất: `backend/data/image_vision_cache.json`, bộ đệm phần chữ đọc từ
  ảnh trên website — nó chép nguyên văn watermark, nên bên trong có số ấy **ba
  mươi lần** cùng ba địa chỉ và mã số thuế công ty

Bảy chỗ cho một mẩu dữ liệu. Không có ca kiểm thử thì lần sau lại bảy chỗ, và lần
sau nữa sẽ có chỗ thứ tám.

## Cách làm: danh sách số giả phải khai tên

Bộ này quét mọi tệp nguồn tìm chuỗi có dạng số điện thoại di động Việt Nam. Số
nào **không** nằm trong `SO_GIA_DA_KHAI` thì ca kiểm thử đỏ.

Nghĩa là thêm một số điện thoại vào kho mã vẫn làm được — nhưng phải khai nó ở
đây, và lúc khai thì người viết buộc phải tự trả lời câu "số này là số thật của
ai". Đó mới là chỗ chặn, chứ không phải bản thân biểu thức chính quy.
"""
import pathlib
import re
import unittest


GOC = pathlib.Path(__file__).resolve().parents[2]

# Số điện thoại di động Việt Nam: mở đầu 03/05/07/08/09, tổng mười chữ số, cho
# phép dấu cách, dấu chấm hoặc gạch ngang xen giữa. Cũng bắt dạng +84/84.
_SO_DIEN_THOAI = re.compile(
    r"(?:(?:\+?84)[.\s-]?|0)(?:3|5|7|8|9)(?:[.\s-]?\d){8}"
)


def _chi_so(chuoi: str) -> str:
    return re.sub(r"\D", "", chuoi)


def _chuan(chuoi: str) -> str:
    """Đưa về mười chữ số bắt đầu bằng 0, để `+84 912…` và `0912…` là một."""
    so = _chi_so(chuoi)
    if so.startswith("84") and len(so) == 11:
        so = "0" + so[2:]
    return so


# Những số được phép có trong kho mã. Mỗi dòng phải nói rõ nó là gì.
SO_GIA_DA_KHAI = {
    "0000000000": "Số giả mặc định khi chưa khai SUPPORT_PHONE",
    "0912345678": "Số ví dụ trong dữ liệu kiểm thử chuẩn hóa số điện thoại",
    "0987654321": "Số ví dụ trong dữ liệu kiểm thử chuẩn hóa số điện thoại",
    "0356789012": "Số ví dụ trong dữ liệu kiểm thử chuẩn hóa số điện thoại",
    "0866777888": "Số ví dụ trong dữ liệu kiểm thử chuẩn hóa số điện thoại",
    "0901234567": "Số ví dụ trong dữ liệu kiểm thử",
    "0934567890": "Số trong CV mẫu do chính bộ sinh CV giả tạo ra",
    "0987123456": "Số trong CV mẫu do chính bộ sinh CV giả tạo ra",
    "0978111222": "Số trong CV mẫu do chính bộ sinh CV giả tạo ra",
    "0914552780": "Số trong CV mẫu do chính bộ sinh CV giả tạo ra",
    "0987331205": "Số trong CV mẫu do chính bộ sinh CV giả tạo ra",
    "0900000000": "Số rõ ràng là giả, dùng trong kiểm thử cổng ứng viên",
    "0988777666": "Số ví dụ trong kiểm thử bộ kiểm chứng câu trả lời",
}

# Thư mục và tệp đem quét. Không quét cả kho: `venv`, `node_modules`, `.next` và
# `storage` đều là thứ không phải nguồn của mình.
VUNG_QUET = (
    "backend/app",
    "backend/ingestion",
    "backend/scripts",
    "backend/tests",
    "backend/main.py",
    "backend/.env.example",
    "frontend/app",
    "frontend/components",
    "frontend/content",
    "frontend/lib",
    "admin-frontend/app",
    "admin-frontend/lib",
    "docs",
    "README.md",
)

DUOI_QUET = {".py", ".ts", ".tsx", ".json", ".md", ".html", ".css", ".example"}


def _cac_tep():
    for muc in VUNG_QUET:
        duong = GOC / muc
        if duong.is_file():
            yield duong
            continue
        if not duong.is_dir():
            continue
        for tep in duong.rglob("*"):
            if not tep.is_file():
                continue
            if "__pycache__" in tep.parts or "node_modules" in tep.parts:
                continue
            # Bỏ qua chính tệp này. Nó buộc phải chứa cả danh sách số giả đã khai
            # lẫn danh sách mảnh địa chỉ cần chặn — không loại ra thì bộ chốt
            # chặn tự bắt chính nó, và thông báo lỗi khi ấy vô nghĩa hoàn toàn.
            if tep.name == pathlib.Path(__file__).name:
                continue
            if tep.suffix in DUOI_QUET or tep.name.endswith(".env.example"):
                yield tep


class KhongCoSoDienThoaiThatTrongKhoMaTests(unittest.TestCase):
    def test_moi_so_trong_nguon_deu_da_khai_la_so_gia(self):
        lot: list[str] = []
        for tep in _cac_tep():
            try:
                noi_dung = tep.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for khop in _SO_DIEN_THOAI.finditer(noi_dung):
                so = _chuan(khop.group())
                if len(so) != 10 or so in SO_GIA_DA_KHAI:
                    continue
                dong = noi_dung[: khop.start()].count("\n") + 1
                lot.append(f"{tep.relative_to(GOC).as_posix()}:{dong} → {khop.group()!r}")

        self.assertEqual(
            lot,
            [],
            "Có số điện thoại chưa khai trong kho mã. Nếu là số giả thì thêm vào "
            "`SO_GIA_DA_KHAI` kèm một dòng nói rõ nó là gì. Nếu là số thật thì "
            "đưa ra cấu hình — `SUPPORT_PHONE` trong `backend/.env`, hoặc "
            "`NEXT_PUBLIC_HOTLINE` trong `frontend/.env.local`.\n  "
            + "\n  ".join(lot),
        )

    def test_mac_dinh_cua_support_phone_la_so_gia(self):
        """Đây là chỗ dễ bị sửa lại nhất: ai đó thấy bất tiện và điền số thật vào."""
        nguon = (GOC / "backend" / "app" / "core" / "config.py").read_text(
            encoding="utf-8"
        )
        dong = next(d for d in nguon.splitlines() if d.strip().startswith("support_phone"))
        self.assertIn("0000.000.000", dong, f"mặc định không còn là số giả: {dong.strip()}")

    def test_frontend_lay_hotline_tu_cau_hinh(self):
        nguon = (GOC / "frontend" / "content" / "site.ts").read_text(encoding="utf-8")
        self.assertIn("NEXT_PUBLIC_HOTLINE", nguon)

    def test_bo_dem_doc_anh_khong_vao_kho(self):
        """Bộ đệm ấy chép nguyên văn watermark trên ảnh của công ty.

        Là dữ liệu dẫn xuất — chạy lại bộ nạp là có lại — nên cái giá của việc
        bỏ nó ra khỏi kho chỉ là một lần gọi lại mô hình đọc ảnh.
        """
        bo_qua = (GOC / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("backend/data/image_vision_cache.json", bo_qua)


class KhongCoDiaChiVanPhongTrongKhoMaTests(unittest.TestCase):
    """Tên thành phố thì được, số nhà và tên đường thì không.

    Tên thành phố có trên mọi giấy tờ giới thiệu và không chỉ tới một địa điểm cụ
    thể. Còn "Tầng 6, Tòa nhà Hữu Nghị, 188 Lê Quang Đạo" thì chỉ đúng một chỗ.
    """

    # Các mảnh địa chỉ đã từng nằm trong kho mã, gom từ lượt dọn ngày 29/09/2026.
    MANH_DIA_CHI = (
        "Lê Quang Đạo",
        "Vạn Phúc",
        "Phan Đình Phùng",
        "Hữu Nghị",
        "201C2",
        "301D",
    )

    def test_khong_con_manh_dia_chi_nao(self):
        lot: list[str] = []
        for tep in _cac_tep():
            try:
                noi_dung = tep.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for manh in self.MANH_DIA_CHI:
                if manh in noi_dung:
                    lot.append(f"{tep.relative_to(GOC).as_posix()} → {manh!r}")
        self.assertEqual(
            lot,
            [],
            "Địa chỉ văn phòng phải khai trong `frontend/.env.local` "
            "(`NEXT_PUBLIC_OFFICE_*_ADDRESS`), không viết vào nguồn.\n  "
            + "\n  ".join(lot),
        )


class KhongNeuTenNguoiThatTrongCauNoiVoiKhachTests(unittest.TestCase):
    """Câu bot nói với khách phải nêu chức danh, không nêu tên riêng.

    Ngày 29/09/2026 câu trả lời dự phòng còn ghi "liên hệ anh Quang qua số …".
    Đứng cạnh số điện thoại, đó là một danh thiếp không ai xin phép để đăng.

    Còn một lý do thực dụng hơn: số hotline nay lấy từ cấu hình, nên máy chưa khai
    sẽ hiện số giả. "Liên hệ anh Quang qua số 0000.000.000" vừa nêu đúng tên người
    vừa cho sai số của họ — khách gọi vào số rỗng rồi nghĩ người ấy cho số sai.
    """

    # Tên riêng đã từng xuất hiện trong câu nói với khách.
    TEN_RIENG = ("anh Quang", "a.Quang", "a.QUANG")

    # Chỉ quét những nơi sinh ra chữ mà khách đọc được. Không quét tài liệu thiết
    # kế: ở đó nhắc tên người trong phần ghi nguồn khảo sát là hợp lý.
    VUNG = (
        "backend/app/conversation",
        "backend/app/advisor",
        "backend/app/consultation",
        "frontend/content",
        "frontend/components",
    )

    def test_khong_con_ten_rieng_nao(self):
        lot: list[str] = []
        for muc in self.VUNG:
            for tep in (GOC / muc).rglob("*"):
                if not tep.is_file() or tep.suffix not in DUOI_QUET:
                    continue
                if "__pycache__" in tep.parts:
                    continue
                noi_dung = tep.read_text(encoding="utf-8")
                for ten in self.TEN_RIENG:
                    if ten in noi_dung:
                        lot.append(f"{tep.relative_to(GOC).as_posix()} → {ten!r}")
        self.assertEqual(
            lot,
            [],
            "Câu nói với khách phải nêu chức danh ('nhân viên tư vấn'), không nêu "
            "tên riêng.\n  " + "\n  ".join(lot),
        )


if __name__ == "__main__":
    unittest.main()
