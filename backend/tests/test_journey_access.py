"""Kiểm thử: biết mã phiên của người khác không đủ để đọc hồ sơ của họ.

## Lỗ hổng được vá ngày 22/09/2026

Bảy đường `/public/*` nhận diện người dùng bằng đúng mã phiên trên URL, không có
gì khác. Chúng trả ra họ tên, **số điện thoại**, câu trích nguyên văn từ CV và
hai mươi tin nhắn gần nhất — và cho **sửa** hồ sơ, **xác nhận hộ**, **đăng ký
hộ**. Máy chủ lại chỉ kiểm hình dạng chuỗi, nên `"a" * 32` cũng là mã hợp lệ.

Mã phiên nằm trên URL thì lọt vào access log, vào header `Referer` gửi sang mọi
trang ngoài, và vào lịch sử trình duyệt. Không nơi nào trong ba nơi ấy được coi
là chỗ giữ bí mật.

## Ba điều lớp test này phải chứng minh

1. **Không cookie thì không vào được** — chặn người chỉ nhặt được mã trên URL.
2. **Cookie của mình không mở được phiên của người khác** — đây là vế dễ quên
   nhất. Nếu chỉ kiểm "cookie hợp lệ" mà không kiểm "cookie nói về đúng phiên
   này", thì ai cũng tự mở một phiên rồi đổi mã trên URL là đọc được hồ sơ
   người khác. Vá kiểu đó còn tệ hơn không vá, vì nó tạo cảm giác đã an toàn.
3. **Không tự khai được mã phiên** — cửa mở phiên phải tự sinh mã, không nhận
   mã client gửi lên. Nhận thì kẻ tấn công chỉ việc gửi mã của nạn nhân rồi
   nhận về một cookie hợp lệ cho hồ sơ người ta.
"""
import time
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.journey import router as journey_router
from app.api.profiles import public_router as profile_router
from app.auth import journey_security as bao_mat
from app.core.config import settings
from app.db import candidate_profiles as store
from tests.cookie_phien import cookies_cho


PHIEN_CUA_TOI = "11111111-2222-3333-4444-555555555555"
PHIEN_NGUOI_KHAC = "99999999-8888-7777-6666-555555555555"

HO_SO_NGUOI_KHAC = {
    "code": "UV-NGUOIKHAC",
    "session_id": PHIEN_NGUOI_KHAC,
    "status": store.STATUS_CONFIRMED,
    "version": 1,
    "fields": {
        "full_name": {"value": "Trần Thị Bích", "source": "cv", "confidence": 0.9},
        "phone": {"value": "0912345678", "source": "cv", "confidence": 0.9},
    },
    "preferences": {},
}


def dung_app() -> FastAPI:
    app = FastAPI()
    app.include_router(journey_router)
    app.include_router(profile_router)
    return app


class KhongCookieThiKhongVaoDuocTests(unittest.TestCase):
    def test_doc_ho_so_ma_khong_co_cookie_thi_bi_tu_choi(self):
        with TestClient(dung_app()) as client:
            response = client.get(f"/public/profiles/{PHIEN_NGUOI_KHAC}")
        self.assertEqual(response.status_code, 401)

    def test_sua_ho_so_ma_khong_co_cookie_thi_bi_tu_choi(self):
        with TestClient(dung_app()) as client:
            response = client.patch(
                f"/public/profiles/{PHIEN_NGUOI_KHAC}",
                json={"fields": {"full_name": "Kẻ lạ"}},
            )
        self.assertEqual(response.status_code, 401)

    def test_xac_nhan_ho_so_ho_nguoi_khac_bi_tu_choi(self):
        # Xác nhận hộ là thao tác mở khoá bộ đối chiếu và mở đường tới đăng ký.
        with TestClient(dung_app()) as client:
            response = client.post(f"/public/profiles/{PHIEN_NGUOI_KHAC}/confirm")
        self.assertEqual(response.status_code, 401)


class CookieCuaMinhKhongMoDuocPhienNguoiKhacTests(unittest.TestCase):
    """Vế dễ quên nhất, và là vế khiến bản vá thật sự có tác dụng."""

    def test_doi_ma_phien_tren_url_thi_bi_chan(self):
        with TestClient(dung_app(), cookies=cookies_cho(PHIEN_CUA_TOI)) as client:
            response = client.get(f"/public/profiles/{PHIEN_NGUOI_KHAC}")

        self.assertEqual(response.status_code, 403)

    def test_du_lieu_ca_nhan_khong_ro_ri_trong_than_phan_hoi(self):
        with TestClient(dung_app(), cookies=cookies_cho(PHIEN_CUA_TOI)) as client:
            response = client.get(f"/public/profiles/{PHIEN_NGUOI_KHAC}")

        than = response.text
        self.assertNotIn("Trần Thị Bích", than)
        self.assertNotIn("0912345678", than)

    def test_dung_phien_cua_minh_thi_van_doc_duoc_binh_thuong(self):
        """Vá xong vẫn phải dùng được — nếu không thì đây là làm hỏng, không phải vá."""
        ho_so_cua_toi = {**HO_SO_NGUOI_KHAC, "session_id": PHIEN_CUA_TOI}
        with patch.object(
            store, "get_by_session", AsyncMock(return_value=ho_so_cua_toi)
        ):
            with TestClient(dung_app(), cookies=cookies_cho(PHIEN_CUA_TOI)) as client:
                response = client.get(f"/public/profiles/{PHIEN_CUA_TOI}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["fields"]["full_name"]["value"], "Trần Thị Bích")


class CookieGiaKhongDungDuocTests(unittest.TestCase):
    def test_sua_mot_ky_tu_trong_chu_ky_la_hong(self):
        token = bao_mat.create_journey_token(PHIEN_CUA_TOI)
        noi_dung, chu_ky = token.rsplit(".", 1)
        # Đổi đúng một ký tự cuối của chữ ký.
        gia = f"{noi_dung}.{chu_ky[:-1]}{'A' if chu_ky[-1] != 'A' else 'B'}"

        self.assertIsNone(bao_mat.read_journey_token(gia))

    def test_doi_ma_phien_ben_trong_token_lam_chu_ky_khong_con_khop(self):
        """Không ký lại được nếu không có khoá — đó là toàn bộ điểm của chữ ký."""
        import base64
        import json

        token = bao_mat.create_journey_token(PHIEN_CUA_TOI)
        noi_dung, chu_ky = token.rsplit(".", 1)
        payload = json.loads(bao_mat._b64decode(noi_dung))
        payload["sid"] = PHIEN_NGUOI_KHAC
        noi_dung_moi = (
            base64.urlsafe_b64encode(json.dumps(payload).encode())
            .rstrip(b"=")
            .decode()
        )

        self.assertIsNone(bao_mat.read_journey_token(f"{noi_dung_moi}.{chu_ky}"))

    def test_token_het_han_thi_khong_dung_duoc(self):
        with patch.object(bao_mat, "TOKEN_DAYS", 0):
            token = bao_mat.create_journey_token(PHIEN_CUA_TOI)
        # Nhích đồng hồ một giây để vượt qua đúng mốc hết hạn.
        with patch.object(time, "time", return_value=time.time() + 1):
            self.assertIsNone(bao_mat.read_journey_token(token))

    def test_chuoi_rac_khong_lam_sap_ung_dung(self):
        for rac in ("", "khong-phai-token", "a.b.c", "....", "x" * 500):
            self.assertIsNone(bao_mat.read_journey_token(rac))


class MoPhienTests(unittest.TestCase):
    def test_mo_phien_moi_thi_dat_cookie_va_tra_ma(self):
        with TestClient(dung_app()) as client:
            response = client.post("/public/phien")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["vua_mo"])
        self.assertIn(settings.journey_cookie_name, response.cookies)

    def test_ma_phien_do_may_chu_sinh_khong_nhan_tu_client(self):
        """Chỗ dễ làm sai nhất trong cả bản vá.

        Nếu cửa này nhận mã phiên client gửi lên rồi cấp cookie cho mã đó, thì
        kẻ tấn công chỉ việc gửi mã của nạn nhân và nhận về một cookie hợp lệ
        cho hồ sơ người ta — vá xong vẫn thủng y như cũ, chỉ khác là bây giờ
        trông có vẻ an toàn.
        """
        with TestClient(dung_app()) as client:
            response = client.post(
                "/public/phien", json={"session_id": PHIEN_NGUOI_KHAC}
            )

        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response.json()["session_id"], PHIEN_NGUOI_KHAC)

    def test_goi_lai_khong_lam_mat_phien_dang_co(self):
        """Tải lại trang không được xoá sạch thứ khách vừa khai."""
        with TestClient(dung_app(), cookies=cookies_cho(PHIEN_CUA_TOI)) as client:
            response = client.post("/public/phien")

        self.assertEqual(response.json()["session_id"], PHIEN_CUA_TOI)
        self.assertFalse(response.json()["vua_mo"])

    def test_cookie_khong_doc_duoc_bang_javascript(self):
        with TestClient(dung_app()) as client:
            response = client.post("/public/phien")

        header = response.headers["set-cookie"].lower()
        self.assertIn("httponly", header)
        self.assertIn("samesite=lax", header)


if __name__ == "__main__":
    unittest.main()
