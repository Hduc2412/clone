"""CV gốc và toàn văn CV không được nằm lại trong bộ đệm trình duyệt.

Lỗi đo được ngày 06/10 trên trình duyệt thật: manager chuyển hồ sơ từ A sang B,
máy chủ trả 403 cho A đúng như quy tắc — nhưng A tải lại CV trên cùng trình duyệt
vẫn ra bản PDF. Log máy chủ không có lời gọi nào: trình duyệt tự trả từ bộ đệm vì
`FileResponse` gửi `ETag`/`Last-Modified` mà không có `Cache-Control`.

Các ca ở đây đi qua HTTP thật (TestClient), vì header là thứ chỉ thấy ở tầng đó.
"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import documents
from app.auth.security import get_current_user

A = {"email": "a@local.test", "role": "consultant", "status": "active"}
TAI_LIEU = {
    "code": "CV-AAAAAA",
    "profile_code": "UV-AAAAAA",
    "stored_path": "cv/2026/10/CV-AAAAAA.pdf",
    "content_type": "application/pdf",
    "filename": "cv.pdf",
    "text": "Họ tên: Nguyễn Văn Mẫu",
}


class CvKhongLuuDemTests(unittest.TestCase):
    def setUp(self):
        thu_muc = tempfile.TemporaryDirectory()
        self.addCleanup(thu_muc.cleanup)
        self.file = Path(thu_muc.name) / "cv.pdf"
        self.file.write_bytes(b"%PDF-1.4 mau")

        app = FastAPI()
        app.include_router(documents.router)
        app.dependency_overrides[get_current_user] = lambda: A
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

        self._va(documents.store, "get_by_code", AsyncMock(return_value=TAI_LIEU))
        self._va(documents.profiles, "get_by_code", AsyncMock(return_value={"code": "UV-AAAAAA"}))
        self._va(documents.storage, "absolute_path", lambda _p: self.file)
        self._va(documents, "audit_action", AsyncMock())

    def _va(self, dich, ten, gia_tri):
        p = patch.object(dich, ten, gia_tri)
        p.start()
        self.addCleanup(p.stop)

    def _quyen(self, *lan):
        """`co_quyen_ho_so` trả lần lượt các giá trị cho từng lần tải."""
        tra = AsyncMock(side_effect=list(lan))
        self._va(documents.quyen_ho_so, "co_quyen_ho_so", tra)
        return tra

    def test_ban_goc_cam_luu_dem(self):
        self._quyen(True)
        r = self.client.get("/documents/CV-AAAAAA/original")
        self.assertEqual(r.status_code, 200)
        self.assertIn("no-store", r.headers.get("cache-control", ""))

    def test_toan_van_cam_luu_dem(self):
        self._quyen(True)
        r = self.client.get("/documents/CV-AAAAAA/text")
        self.assertEqual(r.status_code, 200)
        self.assertIn("no-store", r.headers.get("cache-control", ""))

    def test_moi_lan_tai_kiem_quyen_lai(self):
        """Đúng thứ tự của lỗi: tải được, rồi mất quyền, tải lại phải 403."""
        tra = self._quyen(True, False)
        self.assertEqual(self.client.get("/documents/CV-AAAAAA/original").status_code, 200)
        self.assertEqual(self.client.get("/documents/CV-AAAAAA/original").status_code, 403)
        self.assertEqual(tra.await_count, 2)


if __name__ == "__main__":
    unittest.main()
