"""Quản lý danh mục khóa học qua API.

Bảng này khác `job_orders` ở một điểm quyết định cách kiểm thử: **đây là dữ liệu
thật của trung tâm, không phải dữ liệu mẫu**. Mười chín đơn hàng là đơn bịa ra để
demo bộ lọc; còn mỗi dòng khóa học là một lời hứa với người đang tính chuyện vay
tiền đi nước ngoài. Nên bộ này canh hai thứ:

1. **Dữ liệu sai luật không vào được bảng**, và luật ấy phải là **cùng một bộ** với
   bộ nạp. Hai cửa vào cùng một bảng với hai mức khắt khe khác nhau thì cửa lỏng
   hơn sẽ nhận những dòng cửa kia từ chối.
2. **Khóa nháp không lọt ra phần tư vấn**, và **khóa đang áp dụng không xóa được**.
"""
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from app.api import courses as api
from app.db import courses as store


QUAN_LY = {"email": "quan.ly@example.com", "role": "manager"}

KHOA_DUNG = {
    "code": "KH-0002",
    "title": "Học tiếng Nhật buổi tối",
    "level_from": "chua_hoc",
    "level_to": "N5",
    "months_min": 4,
    "months_max": 5,
    "tuition_vnd": 20_000_000,
    "package_total_vnd": 90_000_000,
    "format": "Học buổi tối, thứ Hai đến thứ Sáu.",
    "curriculum": "Minna no Nihongo Sơ cấp, 25 bài đầu",
    "status": store.STATUS_DRAFT,
    "source_url": "https://xklddieuduong.vn/",
    "source_note": "Chủ đầu tư chốt ngày 29/09/2026",
}


def body(**ghi_de):
    return api.KhoaHocTaoMoiBody(**{**KHOA_DUNG, **ghi_de})


def _request():
    from fastapi import Request

    return Request({"type": "http", "headers": [], "client": ("127.0.0.1", 1234)})


class LuatHopLeDungChungVoiBoNapTests(unittest.TestCase):
    """Luật nằm ở `app/db/courses.kiem_tra`, cả API lẫn bộ nạp đều gọi nó."""

    def test_bo_nap_goi_dung_ham_cua_tang_du_lieu(self):
        """Canh để không ai chép lại bộ luật thành bản thứ hai.

        Trước 29/09 luật chỉ nằm trong `scripts/seed_courses.py`. Mở API mà không
        gom lại thì thành hai bộ luật, và chúng sẽ trôi xa nhau lặng lẽ.
        """
        import pathlib

        nguon = (
            pathlib.Path(__file__).resolve().parent.parent
            / "scripts" / "seed_courses.py"
        ).read_text(encoding="utf-8")
        self.assertIn("courses.kiem_tra(entry)", nguon)

    def test_khai_nguoc_trinh_do_bi_tu_choi(self):
        """Sai nguy hiểm nhất, vì nó hỏng trong im lặng.

        Bộ ghép lộ trình bỏ qua khóa khai ngược mà không báo gì; triệu chứng duy
        nhất là ứng viên không bao giờ nhận được lộ trình học.
        """
        with self.assertRaises(store.KhoaHocKhongHopLe) as ctx:
            store.kiem_tra({**KHOA_DUNG, "level_from": "N4", "level_to": "chua_hoc"})
        self.assertIn("nâng trình độ lên", str(ctx.exception))

    def test_cung_trinh_do_cung_bi_tu_choi(self):
        """Khóa từ N4 lên N4 không đưa ai đi đâu."""
        with self.assertRaises(store.KhoaHocKhongHopLe):
            store.kiem_tra({**KHOA_DUNG, "level_from": "N4", "level_to": "N4"})

    def test_trinh_do_ngoai_danh_muc_bi_tu_choi(self):
        with self.assertRaises(store.KhoaHocKhongHopLe):
            store.kiem_tra({**KHOA_DUNG, "level_to": "N0"})

    def test_tong_goi_nho_hon_hoc_phi_bi_tu_choi(self):
        """Một trong hai con số đang sai, và cả hai đều là tiền của khách."""
        with self.assertRaises(store.KhoaHocKhongHopLe) as ctx:
            store.kiem_tra(
                {**KHOA_DUNG, "tuition_vnd": 90_000_000, "package_total_vnd": 35_000_000}
            )
        self.assertIn("tổng gói", str(ctx.exception))

    def test_so_thang_toi_da_nho_hon_toi_thieu_bi_tu_choi(self):
        with self.assertRaises(store.KhoaHocKhongHopLe):
            store.kiem_tra({**KHOA_DUNG, "months_min": 6, "months_max": 4})

    def test_thieu_truong_bat_buoc_bi_tu_choi(self):
        with self.assertRaises(store.KhoaHocKhongHopLe) as ctx:
            store.kiem_tra({**KHOA_DUNG, "title": ""})
        self.assertIn("title", str(ctx.exception))

    def test_trang_thai_la_bi_tu_choi(self):
        with self.assertRaises(store.KhoaHocKhongHopLe):
            store.kiem_tra({**KHOA_DUNG, "status": "dang_mo"})

    def test_de_trong_hoc_phi_thi_van_hop_le(self):
        """Bảng này giữ con số CÓ NGUỒN. Thà thiếu một ô hơn điền phỏng đoán."""
        store.kiem_tra({**KHOA_DUNG, "tuition_vnd": None, "package_total_vnd": None})

    def test_khoa_dung_thi_qua(self):
        store.kiem_tra(dict(KHOA_DUNG))


class TaoVaSuaTests(unittest.IsolatedAsyncioTestCase):
    async def test_tao_khoa_hop_le(self):
        tao = AsyncMock(return_value=dict(KHOA_DUNG))
        with patch.object(store, "create_course", tao), patch.object(
            api, "audit_action", AsyncMock()
        ):
            ra = await api.tao_moi(body(), _request(), QUAN_LY)
        self.assertEqual(ra["code"], "KH-0002")
        tao.assert_awaited_once()

    async def test_tao_khoa_sai_luat_thi_khong_ghi_gi(self):
        tao = AsyncMock()
        with patch.object(store, "create_course", tao):
            with self.assertRaises(HTTPException) as ctx:
                await api.tao_moi(
                    body(level_from="N4", level_to="N5", months_min=3),
                    _request(),
                    QUAN_LY,
                )
        # N4 → N5 là đi xuống: N5 dễ hơn N4.
        self.assertEqual(ctx.exception.status_code, 422)
        tao.assert_not_awaited()

    async def test_sua_kiem_tren_ban_ghi_sau_khi_tron(self):
        """Sửa một ô có thể làm cả dòng sai luật.

        Ở đây khóa đang là `chua_hoc → N5`; đổi riêng `level_to` thành `chua_hoc`
        thì dòng thành vô nghĩa. Kiểm từng ô rời sẽ không bắt được, vì bản thân
        `"chua_hoc"` là một trình độ hợp lệ.
        """
        ghi = AsyncMock()
        with patch.object(
            store, "get_course", AsyncMock(return_value=dict(KHOA_DUNG))
        ), patch.object(store, "update_course", ghi):
            with self.assertRaises(HTTPException) as ctx:
                await api.sua(
                    "KH-0002",
                    api.KhoaHocBody(
                        **{k: v for k, v in KHOA_DUNG.items() if k != "code"}
                        | {"level_to": "chua_hoc"}
                    ),
                    _request(),
                    QUAN_LY,
                )
        self.assertEqual(ctx.exception.status_code, 422)
        ghi.assert_not_awaited()

    async def test_sua_khoa_khong_ton_tai_thi_404(self):
        with patch.object(store, "get_course", AsyncMock(return_value=None)):
            with self.assertRaises(HTTPException) as ctx:
                await api.sua(
                    "KH-9999",
                    api.KhoaHocBody(**{k: v for k, v in KHOA_DUNG.items() if k != "code"}),
                    _request(),
                    QUAN_LY,
                )
        self.assertEqual(ctx.exception.status_code, 404)


class XoaChiDanhChoKhoaNhapTests(unittest.IsolatedAsyncioTestCase):
    """Khóa đang áp dụng có thể nằm trong lộ trình ai đó vừa được tư vấn."""

    async def test_xoa_duoc_khoa_nhap(self):
        xoa = AsyncMock(return_value=True)
        with patch.object(
            store, "get_course",
            AsyncMock(return_value={**KHOA_DUNG, "status": store.STATUS_DRAFT}),
        ), patch.object(store, "delete_course", xoa), patch.object(
            api, "audit_action", AsyncMock()
        ):
            ra = await api.xoa("KH-0002", _request(), QUAN_LY)
        self.assertTrue(ra["deleted"])
        xoa.assert_awaited_once()

    async def test_khong_xoa_duoc_khoa_dang_ap_dung(self):
        xoa = AsyncMock()
        with patch.object(
            store, "get_course",
            AsyncMock(return_value={**KHOA_DUNG, "status": store.STATUS_PUBLISHED}),
        ), patch.object(store, "delete_course", xoa):
            with self.assertRaises(HTTPException) as ctx:
                await api.xoa("KH-0002", _request(), QUAN_LY)
        self.assertEqual(ctx.exception.status_code, 409)
        # Thông báo phải chỉ đúng đường đi tiếp, không chỉ nói "không được".
        self.assertIn("nháp", ctx.exception.detail)
        xoa.assert_not_awaited()


class KhoaNhapKhongLotRaPhanTuVanTests(unittest.IsolatedAsyncioTestCase):
    async def test_list_published_chi_lay_khoa_dang_ap_dung(self):
        """Khóa khai dở với học phí để trống mà lọt vào lộ trình thì ứng viên nhận
        một con đường học không có giá tiền — tệ hơn không nhận gì, vì họ tưởng
        mình đã biết đủ để quyết định."""
        goi = AsyncMock(return_value=[])
        with patch.object(store, "list_courses", goi):
            await store.list_published()
        self.assertEqual(goi.await_args.kwargs["status"], store.STATUS_PUBLISHED)


class DanhMucChoBieuMauTests(unittest.IsolatedAsyncioTestCase):
    async def test_meta_tra_ve_trinh_do_theo_thu_tu_tu_de_len_kho(self):
        ra = await api.meta(QUAN_LY)
        gia_tri = [m["value"] for m in ra["levels"]]
        self.assertEqual(gia_tri[0], "chua_hoc")
        self.assertEqual(gia_tri[-1], "N1")
        # Nhãn phải là chữ người đọc được, không phải mã máy.
        self.assertEqual(ra["levels"][0]["label"], "Chưa học")

    async def test_meta_tra_ve_du_hai_trang_thai(self):
        ra = await api.meta(QUAN_LY)
        self.assertEqual(
            {m["value"] for m in ra["statuses"]},
            {store.STATUS_PUBLISHED, store.STATUS_DRAFT},
        )


if __name__ == "__main__":
    unittest.main()
