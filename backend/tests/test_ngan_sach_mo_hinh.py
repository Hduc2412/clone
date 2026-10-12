"""Bộ đếm ngân sách lượt gọi mô hình thật (yêu cầu 08/10).

Đây là chốt chặn của luật "tối đa 8 lượt, dừng khi 429 hoặc hai lỗi dịch vụ liên
tiếp". Nó mà hỏng thì một đợt đo có thể âm thầm tiêu quá hạn mức — nên kiểm bằng
transport giả, không một yêu cầu nào rời máy.
"""
import unittest

import httpx

from scripts.ngan_sach_mo_hinh import NganSach

URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-x:generateContent"


class NganSachTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._goc = httpx.AsyncClient.post
        self.da_toi_may_chu = 0

    def tearDown(self):
        httpx.AsyncClient.post = self._goc

    def _client(self, ma_tra: list[int]):
        hang = list(ma_tra)

        def xu_ly(request):
            self.da_toi_may_chu += 1
            return httpx.Response(hang.pop(0) if hang else 200, json={})

        return httpx.AsyncClient(transport=httpx.MockTransport(xu_ly))

    async def test_qua_tran_thi_chan_truoc_khi_roi_may(self):
        ns = NganSach(2).gan()
        async with self._client([200, 200, 200]) as c:
            await c.post(URL, json={})
            await c.post(URL, json={})
            with self.assertRaises(httpx.ConnectError):
                await c.post(URL, json={})
        self.assertEqual(self.da_toi_may_chu, 2)
        self.assertEqual(ns.da_goi, 2)
        self.assertIn("hết ngân sách", ns.ly_do_dung)

    async def test_gap_429_thi_dung_ngay(self):
        ns = NganSach(8).gan()
        async with self._client([429, 200]) as c:
            await c.post(URL, json={})
            with self.assertRaises(httpx.ConnectError):
                await c.post(URL, json={})
        self.assertEqual(self.da_toi_may_chu, 1)
        self.assertEqual(ns.ly_do_dung, "gặp 429")

    async def test_hai_loi_dich_vu_lien_tiep_thi_dung(self):
        ns = NganSach(8).gan()
        async with self._client([503, 503, 200]) as c:
            await c.post(URL, json={})
            await c.post(URL, json={})
            with self.assertRaises(httpx.ConnectError):
                await c.post(URL, json={})
        self.assertEqual(self.da_toi_may_chu, 2)
        self.assertEqual(ns.ly_do_dung, "hai lỗi dịch vụ liên tiếp")

    async def test_loi_xen_ke_lan_dat_thi_chua_dung(self):
        ns = NganSach(8).gan()
        async with self._client([503, 200, 503, 200]) as c:
            for _ in range(4):
                await c.post(URL, json={})
        self.assertFalse(ns.da_dung)
        self.assertEqual(ns.da_goi, 4)

    async def test_het_gio_cho_cung_tinh_la_loi_dich_vu(self):
        ns = NganSach(8).gan()

        def xu_ly(request):
            self.da_toi_may_chu += 1
            raise httpx.ReadTimeout("chậm", request=request)

        async with httpx.AsyncClient(transport=httpx.MockTransport(xu_ly)) as c:
            for _ in range(2):
                with self.assertRaises(httpx.ReadTimeout):
                    await c.post(URL, json={})
            with self.assertRaises(httpx.ConnectError):
                await c.post(URL, json={})
        self.assertEqual(self.da_toi_may_chu, 2)
        self.assertEqual([l["ket_qua"] for l in ns.nhat_ky], ["ReadTimeout", "ReadTimeout"])

    async def test_may_chu_khac_khong_bi_dem(self):
        ns = NganSach(1).gan()
        async with self._client([200, 200, 200]) as c:
            await c.post("http://localhost:6333/collections", json={})
            await c.post("http://localhost:6333/collections", json={})
            await c.post(URL, json={})
        self.assertEqual(ns.da_goi, 1)
        self.assertFalse(ns.da_dung)


class TraLaiBanVaTests(unittest.TestCase):
    """`go()` trả `httpx.AsyncClient.post` về như cũ — bản vá không được sống tiếp (12/10)."""

    def test_go_tra_lai_ham_goc_va_goi_hai_lan_khong_hong(self):
        goc = httpx.AsyncClient.post
        ns = NganSach(1).gan()
        self.assertIsNot(httpx.AsyncClient.post, goc)
        ns.go()
        self.assertIs(httpx.AsyncClient.post, goc)
        ns.go()
        self.assertIs(httpx.AsyncClient.post, goc)

    def test_nghiem_thu_agent_khong_de_lai_ban_va_va_cau_hinh(self):
        import asyncio
        import sys
        from unittest.mock import patch

        from app.core.config import settings
        from scripts import nghiem_thu_agent as agent

        goc = httpx.AsyncClient.post
        cu = (settings.advisor_model, settings.advisor_model_du_phong)
        with patch.object(sys, "argv", ["x", "--gioi-han=0"]), patch.object(agent, "doc_bang", return_value={}), \
             patch.object(agent, "ghi_bang"):
            asyncio.run(agent.main())
        self.assertIs(httpx.AsyncClient.post, goc)
        self.assertEqual((settings.advisor_model, settings.advisor_model_du_phong), cu)


if __name__ == "__main__":
    unittest.main()
