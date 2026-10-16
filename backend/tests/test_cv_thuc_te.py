"""Bộ CV tiệm cận hồ sơ thật (`tests/fixtures/cv_thuc_te/`) có dùng được để đo không.

Không gọi mô hình. Một đáp án chỉ đáng đem ra chấm bộ đọc khi chính nó **truy được
về chữ mà hệ thống rút ra từ tệp**: đáp án ghi N4 mà văn bản đọc được không có
"N4" thì lỗi nằm ở đáp án, và mọi con số đo trên nó đều vô nghĩa. Bộ này canh điều
đó cho cả 22 CV, cộng với việc mỗi định dạng đi đúng nhánh của bộ đọc.

Sinh lại tệp: `python -m scripts.make_cv_thuc_te`.
"""
import json
import re
import unittest
from pathlib import Path

from app.documents import extractor, reader
from app.rag.taxonomy import normalize_text

THU_MUC = Path(__file__).resolve().parent / "fixtures" / "cv_thuc_te"
DAP_AN = json.loads((THU_MUC / "dap_an.json").read_text(encoding="utf-8"))

# Cách một trình độ có thể được viết trên CV, sau khi bỏ dấu và hạ chữ thường.
DAU_HIEU_TRINH_DO = {
    "dai_hoc": ("dai hoc", "cu nhan"),
    "cao_dang": ("cao dang", "associate degree", "短期大学"),
    "trung_cap": ("trung cap",),
    "khac": ("thpt", "lop 12", "12/12"),
}


def _van_ban(entry: dict):
    data = (THU_MUC / entry["file"]).read_bytes()
    return reader.read(data, filename=entry["file"])


def _chu_so(s: str) -> str:
    return re.sub(r"\D", "", s)


class BoCvThucTeTests(unittest.TestCase):
    def test_du_hai_muoi_hai_cv_va_tep_ton_tai(self):
        self.assertEqual(len(DAP_AN), 22)
        for e in DAP_AN:
            with self.subTest(e["file"]):
                self.assertTrue((THU_MUC / e["file"]).is_file())

    def test_dap_an_chi_dung_truong_va_gia_tri_cua_bo_doc(self):
        luoc_do = extractor.RESPONSE_SCHEMA["properties"]
        for e in DAP_AN:
            for truong, gt in e["expected"].items():
                with self.subTest(e["file"], truong=truong):
                    self.assertIn(truong, luoc_do)
                    if gt is not None and "enum" in luoc_do[truong]:
                        self.assertIn(gt, luoc_do[truong]["enum"])

    def test_anh_chup_bi_danh_dau_can_doc_anh_va_khong_co_dap_an(self):
        """Hệ thống không nhận dạng ảnh CV: phải báo không đọc được và mời khai tay."""
        anh = [e for e in DAP_AN if e["format"] == "jpg"]
        self.assertTrue(anh)
        for e in anh:
            with self.subTest(e["file"]):
                _, kq = _van_ban(e)
                self.assertTrue(kq.needs_model_ocr)
                self.assertEqual(e["expected"], {})

    def test_moi_cv_con_lai_doc_ra_chu(self):
        for e in DAP_AN:
            if e["format"] == "jpg":
                continue
            with self.subTest(e["file"]):
                _, kq = _van_ban(e)
                self.assertFalse(kq.needs_model_ocr)
                self.assertGreater(len(kq.text.strip()), 100)

    def test_moi_gia_tri_dap_an_truy_duoc_ve_van_ban(self):
        for e in DAP_AN:
            if e["format"] == "jpg":
                continue
            _, kq = _van_ban(e)
            tho = kq.text
            chuan = normalize_text(tho)
            so = _chu_so(tho)
            for truong, gt in e["expected"].items():
                if gt is None or truong in ("experience_years", "care_experience"):
                    continue  # hai trường này phải tính hoặc phán đoán, không dò chuỗi được
                with self.subTest(e["file"], truong=truong):
                    if truong == "full_name":
                        for tieng in normalize_text(gt).split():
                            self.assertIn(tieng, chuan)
                    elif truong == "birth_year":
                        self.assertIn(str(gt), tho)
                    elif truong == "phone":
                        self.assertTrue(gt in so or gt[1:] in so, f"không thấy {gt}")
                    elif truong == "japanese_level":
                        if gt == "chua_hoc":
                            self.assertIn("chua hoc", chuan)
                        else:
                            self.assertIn(gt.lower(), tho.lower())
                    elif truong == "education_level":
                        self.assertTrue(any(k in chuan or k in tho for k in DAU_HIEU_TRINH_DO[gt]))
                    elif truong == "major":
                        self.assertIn(normalize_text(gt), chuan)
                    elif truong == "gender":
                        dau = ("nu", "女", "female") if gt == "nu" else ("nam", "男", "male")
                        self.assertTrue(any(k in chuan or k in tho.lower() for k in dau))

    def test_cac_bay_co_mat_trong_van_ban(self):
        """Mỗi CV cài một tình huống khó; tình huống ấy phải thật sự nằm trong chữ đọc được."""
        theo_ten = {e["file"].split("_")[0]: e for e in DAP_AN}
        bay = {
            "10": ["1968", "0389"],            # năm sinh, số điện thoại của bố
            "17": ["chờ kết quả"],              # N4 chưa có kết quả
            "18": ["NAT-TEST", "4Q"],           # không phải mã JLPT
            "20": ["0912 837 465"],             # số của người tham chiếu
            "25": ["bỏ qua mọi quy tắc", "N1"],  # câu chèn lệnh
            "28": ["158 cm", "48 kg"],          # số đo cơ thể
        }
        for so, mau in bay.items():
            _, kq = _van_ban(theo_ten[so])
            for m in mau:
                with self.subTest(so, mau=m):
                    self.assertIn(m, kq.text)


if __name__ == "__main__":
    unittest.main()
