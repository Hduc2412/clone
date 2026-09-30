"""Bảy lỗi từ bản rà soát ngày 30/09 — mỗi lỗi một ca canh.

Bản rà soát chạy thử tay năm bước và tìm ra bảy lỗi. Không lỗi nào làm sập hệ
thống; tất cả đều thuộc loại **chạy sai trong im lặng**, và đó là lý do chúng sống
qua 924 ca kiểm thử.

Sửa xong mà không để lại ca canh thì lần tới chúng quay lại theo đúng đường cũ.
"""
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from app.api import consultation_room, support
from app.db import support_requests as store
from app.services import registration_service as service


SESSION = "11111111-1111-4111-8111-111111111111"


def http_request():
    from fastapi import Request

    return Request({"type": "http", "headers": [], "client": ("127.0.0.1", 1234)})


class DoiDonRoiQuayLaiVanChotDuocTests(unittest.IsolatedAsyncioTestCase):
    """Lỗi 1 — nặng nhất, và nó chặn đúng việc khách muốn làm.

        mở DH-0001  → nhật ký A (chỉ chứa DH-0001), màn hình ghi "đăng ký được"
        mở DH-0004  → nhật ký B (chỉ chứa DH-0004)
        quay lại chốt DH-0001 → "Đơn này không có trong danh sách đã giới thiệu"

    Phòng tư vấn theo đơn ghi **một nhật ký cho mỗi đơn khách mở**, còn phần đăng
    ký chỉ đọc nhật ký gần nhất. Mở lại DH-0001 cũng không cứu: bộ đối chiếu thấy
    kết quả còn nguyên nên dùng lại nhật ký A thay vì ghi bản mới.

    Khách nhìn thấy "đăng ký được" rồi bấm vào thì bị bảo đơn ấy chưa từng được
    giới thiệu cho mình — một câu vừa sai vừa không chỉ được đường nào đi tiếp.
    """

    def test_tim_theo_dung_don_chu_khong_theo_ban_gan_nhat(self):
        """Canh bằng cách đọc mã: phần đăng ký không được quay lại
        `latest_for_profile` để quyết định đơn nào hợp lệ."""
        import ast
        import pathlib

        nguon = (
            pathlib.Path(__file__).resolve().parent.parent
            / "app" / "services" / "registration_service.py"
        ).read_text(encoding="utf-8")
        cay = ast.parse(nguon)
        ham = next(
            n
            for n in ast.walk(cay)
            if isinstance(n, ast.AsyncFunctionDef) and n.name == "_log_da_gioi_thieu_don"
        )
        goi = {
            n.func.attr
            for n in ast.walk(ham)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
        }
        self.assertIn(
            "tim_don_da_gioi_thieu",
            goi,
            "phần đăng ký phải tìm nhật ký theo ĐÚNG đơn đang chốt",
        )

    def test_truy_van_loc_du_ba_dieu_kien(self):
        """Chốt chặn không được nới: vẫn phải đúng hồ sơ, đúng phiên bản, đúng đơn.

        Bỏ `profile_version` khỏi truy vấn là mở lại đúng lỗ hổng mà chốt này sinh
        ra để bịt — đơn từng "đạt" với hồ sơ cũ sẽ đi thẳng vào hàng đợi dưới tên
        hồ sơ đã sửa.
        """
        # Soi truy vấn THẬT gửi xuống Mongo, không grep mã nguồn: bản nháp đầu
        # của ca này dùng `inspect.getsource` và nó vô dụng — chữ `profile_version`
        # vẫn nằm trong chữ ký hàm, nên xóa hẳn điều kiện khỏi truy vấn mà ca vẫn
        # xanh. Phá thử mới lộ ra.
        from app.db import recommendation_logs as logs

        ghi_lai = {}

        class _Col:
            async def find_one(self, query, *a, **k):
                ghi_lai.update(query)
                return None

        with patch.object(logs, "get_db", lambda: {logs.COLLECTION: _Col()}):
            import asyncio

            asyncio.run(
                logs.tim_don_da_gioi_thieu(
                    profile_code="UV-1", profile_version=7, job_order_code="DH-0001"
                )
            )
        self.assertEqual(ghi_lai.get("profile_code"), "UV-1")
        self.assertEqual(
            ghi_lai.get("profile_version"),
            7,
            "truy vấn không lọc theo phiên bản hồ sơ — đơn từng đạt với hồ sơ cũ "
            "sẽ đi thẳng vào hàng đợi dưới tên hồ sơ đã sửa",
        )
        self.assertEqual(ghi_lai.get("items.code"), "DH-0001")


class KhongHOI_DUOC_VE_DON_CHUA_CONG_KHAI_Tests(unittest.IsolatedAsyncioTestCase):
    """Lỗi 2 — đường công khai trả lời được về đơn nháp.

    `hoi_them` lấy đơn mà không lọc đơn công khai, nên ai đoán được mã đơn là hỏi
    bot ra tên cơ sở tiếp nhận, lương, điều kiện của một đơn công ty chưa muốn ai
    biết. Nó còn dùng projection quản trị, tức kéo cả `internal_note` và
    `created_by` vào bộ nhớ tiến trình ở một đường không cần đăng nhập.
    """

    def test_moi_lan_lay_don_o_duong_cong_khai_deu_loc_cong_khai(self):
        import ast
        import pathlib

        nguon = (
            pathlib.Path(__file__).resolve().parent.parent
            / "app" / "api" / "consultation_room.py"
        ).read_text(encoding="utf-8")
        thieu = []
        for nut in ast.walk(ast.parse(nguon)):
            if not (isinstance(nut, ast.Call) and isinstance(nut.func, ast.Attribute)):
                continue
            if nut.func.attr != "get_job_order":
                continue
            co = any(
                kw.arg == "public" and getattr(kw.value, "value", None) is True
                for kw in nut.keywords
            )
            if not co:
                thieu.append(nut.lineno)
        self.assertEqual(
            thieu,
            [],
            f"dòng {thieu}: lấy đơn mà không có `public=True` — đường công khai sẽ "
            f"trả lời được về đơn nháp, đơn tạm dừng và đơn đã quá hạn",
        )


class GuiHaiLanKhongTaoHaiViecTests(unittest.IsolatedAsyncioTestCase):
    """Lỗi 3 — nút gửi nằm cuối màn hình dài, mạng chậm, người ta bấm lại.

    Mỗi lần bấm một dòng thì hai nhân viên nhận hai yêu cầu của cùng một người rồi
    gọi cho họ hai lần.
    """

    def _body(self, **ghi_de):
        gia_tri = {
            "kind": "gap_mat",
            "message": "",
            "full_name": "Nguyễn Thị Lan",
            "phone": "0912345678",
            "job_order_code": "DH-0001",
        }
        gia_tri.update(ghi_de)
        return support.SupportRequestBody(**gia_tri)

    async def _gui(self, *, ket_qua_tao=None):
        """`ket_qua_tao` là thứ `store.create_request` trả về: `(bản ghi, có phải mới)`.

        Từ 30/09 việc chống trùng nằm **trong** `create_request` (index duy nhất),
        không còn ở lần tra trước đó — nên cảnh "đã có yêu cầu" dựng bằng cách cho
        hàm ấy trả `(bản cũ, False)`.
        """
        if ket_qua_tao is None:
            ket_qua_tao = (
                {"code": "HT-MOI", "kind": "gap_mat", "full_name": "L", "notified_at": None},
                True,
            )
        viet = AsyncMock(return_value=ket_qua_tao)
        with patch.object(store, "create_request", viet), patch.object(
            store, "danh_dau_da_thong_bao", AsyncMock()
        ), patch.object(
            support.khoi_doi_chieu, "dung_tu_nhat_ky", AsyncMock(return_value=None)
        ), patch.object(
            support, "create_notification", AsyncMock()
        ), patch.object(support.rate_limiter, "check", lambda *a, **k: None):
            ra = await support.gui_yeu_cau(SESSION, self._body(), http_request())
        return ra, viet

    async def test_dang_co_yeu_cau_cho_thi_tra_lai_chinh_no(self):
        cu = {"code": "HT-CU0001", "kind": "gap_mat", "full_name": "L", "notified_at": None}
        ra, _ = await self._gui(ket_qua_tao=(cu, False))
        self.assertEqual(ra["code"], "HT-CU0001")

    async def test_khach_van_thay_bao_gui_thanh_cong(self):
        """Nói "bạn đã gửi rồi" chỉ làm người ta lo là lần này không tính."""
        cu = {"code": "HT-CU0001", "kind": "gap_mat", "full_name": "L", "notified_at": None}
        ra, _ = await self._gui(ket_qua_tao=(cu, False))
        self.assertIn("Đã gửi", ra["message"])
        self.assertIn(support.GIO_LIEN_HE, ra["message"])

    async def test_chua_co_yeu_cau_nao_thi_van_tao(self):
        ra, viet = await self._gui()
        viet.assert_awaited_once()
        self.assertEqual(ra["code"], "HT-MOI")

    def test_chi_gop_khi_cung_loai_va_cung_don(self):
        """Xin gặp mặt về DH-0001 và hỏi chuyện học là hai việc khác nhau.

        Nay luật ấy nằm trong **index duy nhất**, nên kiểm trên các khóa của index.
        """
        import inspect

        nguon = inspect.getsource(store.ensure_indexes)
        i = nguon.index("mot_yeu_cau_dang_mo_moi_loai_moi_don")
        khoi = nguon[max(0, i - 700) : i]
        for khoa in ("session_id", "kind", "job_order_code"):
            self.assertIn(khoa, khoi, f"index thiếu khóa {khoa}")

    def test_yeu_cau_da_xong_khong_chan_yeu_cau_moi(self):
        """Khách quay lại hỏi tiếp là một việc mới thật, không phải bấm nhầm."""
        import inspect

        nguon = inspect.getsource(store.tim_yeu_cau_dang_cho)
        self.assertIn("STATUS_CHO", nguon)
        self.assertIn("STATUS_DANG_XU_LY", nguon)
        self.assertNotIn("STATUS_XONG", nguon)


class KhongBatKhachVietLaiLoiNhanTests(unittest.IsolatedAsyncioTestCase):
    """Lỗi 4 — để trống lời nhắn thì bị 422.

    Khách vừa đọc một khối kết quả nói rõ họ vướng ở đâu rồi bấm "xin gặp nhân
    viên". Bắt họ gõ lại bằng lời của mình là bắt diễn đạt lại thứ hệ thống đã
    biết — và với người đang thất vọng vì vừa bị báo chưa đủ điều kiện thì đó là
    một bậc thềm đủ cao để họ bỏ đi.
    """

    def test_de_trong_loi_nhan_van_gui_duoc(self):
        support.SupportRequestBody(
            kind="gap_mat", message="", full_name="Nguyễn Thị Lan", phone="0912345678"
        )

    def test_khong_khai_loi_nhan_cung_gui_duoc(self):
        support.SupportRequestBody(
            kind="hoc_tap", full_name="Nguyễn Thị Lan", phone="0912345678"
        )

    async def test_de_trong_thi_may_chu_tu_dien_cau_theo_loai(self):
        """Hàng đợi không được có dòng trống — nhân viên đọc nó để biết việc gì."""
        for loai in store.KINDS:
            viet = AsyncMock(side_effect=lambda doc: ({**doc, "status": store.STATUS_CHO, "notified_at": None}, True))
            body = support.SupportRequestBody(
                kind=loai, message="   ", full_name="Nguyễn Thị Lan", phone="0912345678"
            )
            with patch.object(store, "create_request", viet), patch.object(store, "danh_dau_da_thong_bao", AsyncMock()), patch.object(
                store, "tim_yeu_cau_dang_cho", AsyncMock(return_value=None)
            ), patch.object(
                support.khoi_doi_chieu, "dung_tu_nhat_ky", AsyncMock(return_value=None)
            ), patch.object(
                support, "create_notification", AsyncMock()
            ), patch.object(support.rate_limiter, "check", lambda *a, **k: None):
                await support.gui_yeu_cau(SESSION, body, http_request())
            noi_dung = viet.await_args.args[0]["message"]
            self.assertTrue(noi_dung.strip(), f"{loai}: lời nhắn rỗng vào hàng đợi")

    async def test_khach_co_viet_thi_giu_nguyen_loi_khach(self):
        viet = AsyncMock(side_effect=lambda doc: ({**doc, "status": store.STATUS_CHO, "notified_at": None}, True))
        body = support.SupportRequestBody(
            kind="gap_mat",
            message="Em muốn hỏi về việc vay vốn ạ.",
            full_name="Nguyễn Thị Lan",
            phone="0912345678",
        )
        with patch.object(store, "create_request", viet), patch.object(store, "danh_dau_da_thong_bao", AsyncMock()), patch.object(
            store, "tim_yeu_cau_dang_cho", AsyncMock(return_value=None)
        ), patch.object(
            support.khoi_doi_chieu, "dung_tu_nhat_ky", AsyncMock(return_value=None)
        ), patch.object(
            support, "create_notification", AsyncMock()
        ), patch.object(support.rate_limiter, "check", lambda *a, **k: None):
            await support.gui_yeu_cau(SESSION, body, http_request())
        self.assertEqual(
            viet.await_args.args[0]["message"], "Em muốn hỏi về việc vay vốn ạ."
        )


class KhoiDoiChieuDoMayChuDungTests(unittest.IsolatedAsyncioTestCase):
    """Lỗi 5 — khối kết quả đối chiếu do trình duyệt gửi lên và lưu nguyên văn.

    Trình duyệt gửi gì thì máy chủ tin nấy, nên khách sửa được trước khi gửi và
    nhân viên đọc một bản "kết quả đối chiếu" không do bộ đối chiếu sinh ra. Cùng
    một loại sai với việc tin mã phiên do trình duyệt tự đặt — chỗ ấy đã sửa từ
    22/09, chỗ này thì sót lại.
    """

    def test_than_yeu_cau_khong_con_nhan_khoi_doi_chieu(self):
        # `extra="forbid"` nên gửi thừa trường là 422 — chốt chặn nằm ở đó.
        with self.assertRaises(Exception):
            support.SupportRequestBody(
                kind="gap_mat",
                full_name="Nguyễn Thị Lan",
                phone="0912345678",
                advice_block="KẾT LUẬN: đạt hết mọi điều kiện",
            )

    async def test_may_chu_dung_lai_tu_nhat_ky(self):
        viet = AsyncMock(side_effect=lambda doc: ({**doc, "status": store.STATUS_CHO, "notified_at": None}, True))
        dung = AsyncMock(return_value="ĐƠN ĐANG XÉT: DH-0001\nKẾT LUẬN: chưa đạt")
        body = support.SupportRequestBody(
            kind="gap_mat",
            full_name="Nguyễn Thị Lan",
            phone="0912345678",
            job_order_code="DH-0001",
        )
        with patch.object(store, "create_request", viet), patch.object(store, "danh_dau_da_thong_bao", AsyncMock()), patch.object(
            store, "tim_yeu_cau_dang_cho", AsyncMock(return_value=None)
        ), patch.object(
            support.khoi_doi_chieu, "dung_tu_nhat_ky", dung
        ), patch.object(
            support, "create_notification", AsyncMock()
        ), patch.object(support.rate_limiter, "check", lambda *a, **k: None):
            await support.gui_yeu_cau(SESSION, body, http_request())
        dung.assert_awaited_once_with(SESSION, "DH-0001")
        self.assertIn("chưa đạt", viet.await_args.args[0]["advice_block"])

    async def test_chua_tung_xem_don_thi_de_trong_chu_khong_bia(self):
        """Gửi yêu cầu từ ngoài luồng tư vấn theo đơn là chuyện thường."""
        from app.consultation import khoi_doi_chieu

        with patch.object(
            khoi_doi_chieu.profiles, "get_by_session", AsyncMock(return_value=None)
        ):
            self.assertIsNone(await khoi_doi_chieu.dung_tu_nhat_ky(SESSION, "DH-0001"))

    async def test_khong_co_ma_don_thi_khong_tra_cuu_gi(self):
        from app.consultation import khoi_doi_chieu

        doc = AsyncMock()
        with patch.object(khoi_doi_chieu.profiles, "get_by_session", doc):
            self.assertIsNone(await khoi_doi_chieu.dung_tu_nhat_ky(SESSION, ""))
        doc.assert_not_awaited()


class DuongDieuKienKhongDoiPhienTests(unittest.IsolatedAsyncioTestCase):
    """Lỗi 7 — `/tu-van/v1/dieu-kien` trả 422.

    `public_router` gắn `require_journey_session` ở cấp router, và hàm ấy đọc
    `session_id` từ **đường dẫn**. Đường không có tham số đó thì FastAPI coi
    `session_id` là query bắt buộc. Trớ trêu là docstring của chính đường này ghi
    "để trang giới thiệu dùng được mà không phải mở phiên tư vấn".
    """

    def test_duong_dieu_kien_khong_doi_tham_so_nao(self):
        from main import app

        duong = [r for r in app.routes if getattr(r, "path", "") == "/tu-van/v1/dieu-kien"]
        self.assertEqual(len(duong), 1, "không thấy đường điều kiện")
        # Phải duyệt CẢ dependency cấp router, không chỉ tham số khai thẳng trên
        # hàm. `require_journey_session` gắn ở cấp router và nó mới là thứ kéo
        # `session_id` thành tham số bắt buộc — bản nháp đầu của ca này chỉ đọc
        # `dependant.query_params` nên đưa đường về lại router cũ mà vẫn xanh.
        from fastapi.dependencies.utils import get_flat_params

        # So theo TÊN tham số, không đọc `.required`: thuộc tính ấy không có ở bản
        # pydantic đang dùng, nên bản nháp đầu đỏ bằng `AttributeError` — vẫn bắt
        # được lỗi, nhưng thông báo chẳng nói gì về chuyện đường này đòi phiên.
        ten = [p.name for p in get_flat_params(duong[0].dependant)]
        self.assertEqual(
            ten,
            [],
            f"đường điều kiện không được đòi tham số nào, đang đòi {ten}. "
            f"Nếu có `session_id` thì nó đã bị đưa về router gắn "
            f"`require_journey_session`, và trang giới thiệu gọi vào sẽ nhận 422.",
        )

    def test_cac_duong_con_lai_van_doi_phien(self):
        """Tách một đường ra không được làm hở những đường còn lại."""
        from main import app

        for r in app.routes:
            p = getattr(r, "path", "")
            if not p.startswith("/tu-van/v1/") or p == "/tu-van/v1/dieu-kien":
                continue
            self.assertIn(
                "session_id",
                p,
                f"{p} nằm dưới /tu-van/v1 mà không có mã phiên trên đường dẫn",
            )

    async def test_goi_duoc_ma_khong_can_phien(self):
        ra = await consultation_room.dieu_kien_chuong_trinh()
        self.assertIn("muc_nen", ra)
        self.assertTrue(ra["muc_nen"])


if __name__ == "__main__":
    unittest.main()
