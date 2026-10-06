"""Agent điều phối tư vấn — mười tám tình huống phải đứng được.

## Vì sao bộ này không gọi mô hình

Mọi lượt gọi mô hình bị vá. Hai lý do, và lý do thứ hai quan trọng hơn:

1. Hạn mức gói miễn phí là 20 lượt mỗi ngày mỗi model. Một bộ kiểm thử tiêu hạn
   mức là một bộ kiểm thử không chạy được lần thứ hai trong ngày.
2. **Một ca đỏ vì hết hạn mức trông y như một ca đỏ vì mã sai.** Đó là loại tín
   hiệu tệ nhất một bộ kiểm thử có thể phát ra.

Phần đo chất lượng thật của mô hình nằm ở `scripts/nghiem_thu_tu_van.py`, chạy
tay, và nó đọc `.env` như bình thường.

## Ba nhóm, và nhóm thứ ba mới là nhóm đáng lo

**Nhóm trạng thái** kiểm `state.suy_ra` — thuần, không I/O. Rẻ và chắc.

**Nhóm điều phối** kiểm luồng một lượt: ngữ cảnh vào, hợp đồng ra, chốt chặn
giữa.

**Nhóm chống lạm dụng** kiểm những thứ mô hình *có thể* làm nếu không ai chặn:
ghi vào trường không cho phép, tự khai nguồn `staff`, tự xác nhận hồ sơ, tự đăng
ký đơn. Những ca này không bảo vệ chống lỗi lập trình — chúng bảo vệ chống **nội
dung do người ngoài gửi vào**, tức là câu hỏi của ứng viên. Một trong số đó có
thể là một câu được viết ra để lừa mô hình.
"""
import unittest
from datetime import timedelta
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.advisor import qa
from app.core.timeutil import local_today
from app.agent import ban_giao, contract, mo_dau, orchestrator, state
from app.api.agent import public_router
from app.db import advisor_turns
from app.db import candidate_profiles as profiles
from tests.cookie_phien import cookies_cho


PHIEN = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
PHIEN_KHAC = "11111111-2222-3333-4444-555555555555"


def ho_so(status: str = "extracted", **them) -> dict:
    goc = {
        "code": "UV-TEST01",
        "session_id": PHIEN,
        "status": status,
        "version": 1,
        "fields": {
            "full_name": {"value": "Trần Thị Thu Hà", "source": "cv"},
            "japanese_level": {"value": "N4", "source": "cv"},
            "education_level": {"value": "cao_dang", "source": "cv"},
        },
        "preferences": {},
    }
    goc.update(them)
    return goc


def nhat_ky(so_dat: int = 2, tong: int = 18) -> dict:
    items = [
        {
            "code": f"DH-{i:04d}",
            "title": f"Đơn số {i}",
            "eligible": True,
            "score": 95 - i,
            "rank": i,
            "soft_rows": [{"label": "Khu vực", "points": 40}],
            "hard_rows": [],
        }
        for i in range(1, so_dat + 1)
    ]
    items.append(
        {
            "code": "DH-9999",
            "eligible": False,
            "hard_rows": [{"label": "Tiếng Nhật", "result": "KHONG_DAT"}],
        }
    )
    return {
        "code": "GT-TEST01",
        "profile_code": "UV-TEST01",
        "total_considered": tong,
        "eligible_count": so_dat,
        "items": items,
    }


# --- Nhóm 1: giai đoạn suy ra từ dữ liệu ---


class GiaiDoanSuyRaTuDuLieuTests(unittest.TestCase):
    """Sáu giai đoạn, sáu bộ dữ liệu vào. Không ca nào hỏi mô hình."""

    def test_1_chua_co_ho_so(self):
        tt = state.suy_ra(profile=None)
        self.assertEqual(tt.stage, state.INTAKE)
        self.assertEqual(tt.hanh_dong.type, state.HD_HOI)
        # Chưa đối chiếu lần nào KHÁC với đối chiếu ra không đơn nào.
        self.assertIsNone(tt.so_don_dat)

    def test_2_vua_gui_cv_thi_cho_xem_lai(self):
        tt = state.suy_ra(profile=ho_so())
        self.assertEqual(tt.stage, state.PROFILE_REVIEW)
        self.assertEqual(tt.hanh_dong.type, state.HD_XAC_NHAN)
        self.assertFalse(tt.da_xac_nhan)

    def test_5_da_xac_nhan_nhung_chua_doi_chieu(self):
        tt = state.suy_ra(profile=ho_so(status="confirmed"))
        self.assertEqual(tt.stage, state.MATCHING)
        self.assertEqual(tt.hanh_dong.type, state.HD_DOI_CHIEU)
        self.assertTrue(tt.da_xac_nhan)

    def test_6_co_don_phu_hop(self):
        tt = state.suy_ra(profile=ho_so(status="confirmed"), log=nhat_ky(so_dat=3))
        self.assertEqual(tt.stage, state.MATCHING)
        self.assertEqual(tt.so_don_dat, 3)

    def test_7_khong_co_don_nao_va_da_du_du_lieu_thi_chuyen_nguoi(self):
        """Không đạt mà đã đủ dữ liệu thì bấm đối chiếu lại cũng ra cùng kết quả."""
        day_du = ho_so(status="confirmed")
        day_du["fields"].update(
            {
                "birth_year": {"value": 1999, "source": "user_confirmed"},
                "gender": {"value": "nu", "source": "user_confirmed"},
                "experience_years": {"value": 3, "source": "user_confirmed"},
            }
        )
        day_du["preferences"] = {
            "desired_prefecture": {"value": "Tokyo", "source": "user_confirmed"},
            "desired_employer_type": {"value": "vien_duong_lao", "source": "user_confirmed"},
            "salary_expectation_jpy": {"value": 190000, "source": "user_confirmed"},
            "budget_vnd": {"value": 90000000, "source": "user_confirmed"},
        }
        tt = state.suy_ra(profile=day_du, log=nhat_ky(so_dat=0))
        self.assertEqual(tt.so_don_dat, 0)
        self.assertEqual(tt.hanh_dong.type, state.HD_NHAN_VIEN)

    def test_7b_khong_co_don_nao_nhung_con_thieu_thi_bo_sung_truoc(self):
        tt = state.suy_ra(profile=ho_so(status="confirmed"), log=nhat_ky(so_dat=0))
        self.assertEqual(tt.so_don_dat, 0)
        self.assertEqual(tt.hanh_dong.type, state.HD_HOI)

    def test_12_agent_nho_don_nguoi_dung_dang_quan_tam(self):
        tt = state.suy_ra(
            profile=ho_so(status="confirmed"), log=nhat_ky(), don_dang_xet="DH-0001"
        )
        self.assertEqual(tt.stage, state.ORDER_CONSULTATION)
        self.assertEqual(tt.don_dang_xet, "DH-0001")
        self.assertIn("DH-0001", tt.as_dict()["interested_order_codes"])

    def test_da_dang_ky_khong_bi_keo_ve_buoc_khai_ho_so(self):
        """Xét từ cuối chuỗi về đầu. Người vừa đăng ký không được nghe 'bạn chưa khai gì'."""
        tt = state.suy_ra(
            profile=ho_so(), log=nhat_ky(), don_da_dang_ky=("DH-0001",)
        )
        self.assertEqual(tt.stage, state.REGISTRATION)

    def test_yeu_cau_ho_tro_cat_ngang_moi_giai_doan(self):
        tt = state.suy_ra(
            profile=None, yeu_cau_dang_mo=("HT-ABC123",)
        )
        self.assertEqual(tt.stage, state.HUMAN_SUPPORT)
        self.assertEqual(tt.hanh_dong.type, state.HD_KHONG)

    def test_8_tieu_chi_chua_ro_khong_bi_coi_la_khong_dat(self):
        """Thiếu dữ liệu không phải là không đạt — và không được đếm như thế."""
        log = nhat_ky(so_dat=0)
        log["items"] = [
            {
                "code": "DH-0001",
                "eligible": False,
                "hard_rows": [
                    {"label": "Độ tuổi", "result": "CHUA_RO"},
                    {"label": "Tiếng Nhật", "result": "KHONG_DAT"},
                ],
            }
        ]
        cau = mo_dau.sau_matching(log)
        self.assertIn("tiếng Nhật", cau)
        self.assertNotIn("Độ tuổi", cau)
        self.assertNotIn("độ tuổi", cau)


# --- Nhóm 2: lượt chủ động và bản bàn giao, không gọi mô hình ---


class LuotChuDongTests(unittest.TestCase):
    def test_3_cv_co_truong_chua_chac_thi_noi_ro_la_may_doc(self):
        cau = mo_dau.sau_khi_doc_cv(ho_so())
        self.assertIn("máy đọc được", cau)
        # Không được khẳng định như thể người đã xác nhận.
        self.assertNotIn("bạn đã xác nhận", cau.lower())

    def test_9_agent_hoi_thong_tin_con_thieu_toi_da_hai_cau(self):
        cau_hoi = orchestrator.cau_hoi_con_thieu(ho_so())
        self.assertGreaterEqual(len(cau_hoi), 1)
        self.assertLessEqual(len(cau_hoi), 2)

    def test_khong_hua_hen_trong_luot_chu_dong(self):
        from app.advisor import phrasing

        for cau in (
            mo_dau.sau_khi_doc_cv(ho_so()),
            mo_dau.sau_matching(nhat_ky(), profile=ho_so()),
            mo_dau.sau_matching(nhat_ky(so_dat=0), profile=ho_so()),
        ):
            thap = cau.lower()
            for cum in phrasing.CUM_TU_CAM + phrasing.CUM_TU_CAM_KET:
                self.assertNotIn(cum, thap, f"lượt chủ động chứa cụm cấm {cum!r}")

    def test_luot_chu_dong_tat_dinh(self):
        """Cùng dữ liệu vào phải ra cùng một câu, không phụ thuộc thứ tự dict."""
        log = nhat_ky(so_dat=0)
        log["items"] = [
            {"code": "A", "eligible": False, "hard_rows": [{"label": "Tiếng Nhật", "result": "KHONG_DAT"}]},
            {"code": "B", "eligible": False, "hard_rows": [{"label": "Độ tuổi", "result": "KHONG_DAT"}]},
        ]
        lan_1 = mo_dau.sau_matching(log)
        log["items"].reverse()
        lan_2 = mo_dau.sau_matching(log)
        self.assertEqual(lan_1, lan_2)


class BanGiaoTests(unittest.TestCase):
    def test_13_ban_giao_tach_da_xac_nhan_voi_chua_xac_nhan(self):
        hs = ho_so()
        hs["fields"]["phone"] = {"value": "0914552780", "source": "user_confirmed"}
        tt = state.suy_ra(profile=hs, log=nhat_ky())
        ban = ban_giao.dung(profile=hs, trang_thai=tt, log=nhat_ky())

        self.assertIn("ỨNG VIÊN ĐÃ XÁC NHẬN", ban)
        self.assertIn("MÁY ĐỌC ĐƯỢC, ỨNG VIÊN CHƯA XÁC NHẬN", ban)
        # Trường đọc từ CV phải nằm dưới khối chưa xác nhận, kèm nhãn nguồn.
        duoi = ban.split("MÁY ĐỌC ĐƯỢC, ỨNG VIÊN CHƯA XÁC NHẬN", 1)[1]
        self.assertIn("[đọc từ CV]", duoi)
        self.assertIn("N4", duoi)
        # Và số điện thoại đã xác nhận thì nằm ở khối trên.
        tren = ban.split("MÁY ĐỌC ĐƯỢC", 1)[0]
        self.assertIn("0914552780", tren)

    def test_13b_ban_giao_neu_ro_cau_tro_ly_chua_tra_loi_duoc(self):
        tt = state.suy_ra(profile=ho_so(), log=nhat_ky())
        ban = ban_giao.dung(
            profile=ho_so(),
            trang_thai=tt,
            log=nhat_ky(),
            luot_hoi=[
                {"question": "Học bao lâu thì đủ?", "source": "mo_hinh"},
                {"question": "Chi phí riêng đơn này?", "source": "khong_biet"},
            ],
        )
        self.assertIn("TRỢ LÝ CHƯA TRẢ LỜI ĐƯỢC", ban)
        phan = ban.split("TRỢ LÝ CHƯA TRẢ LỜI ĐƯỢC", 1)[1]
        self.assertIn("Chi phí riêng đơn này?", phan)
        self.assertNotIn("Học bao lâu thì đủ?", phan)

    def test_13e_ban_giao_khong_liet_ke_luot_he_thong_nhu_cau_khach_hoi(self):
        """Lượt Agent tự mở đầu không phải câu ứng viên hỏi.

        Bắt được trên trình duyệt thật 01/10: bản bàn giao in ra hai dòng
        "- [hệ thống] sau_cv" và "- [hệ thống] sau_matching" dưới tiêu đề ỨNG
        VIÊN ĐÃ HỎI. Giao diện phía khách đã ẩn chúng, nhưng bản bàn giao đi một
        đường khác — nên nhân viên là người duy nhất phải đọc hai dòng vô nghĩa.
        """
        tt = state.suy_ra(profile=ho_so(), log=nhat_ky())
        ban = ban_giao.dung(
            profile=ho_so(),
            trang_thai=tt,
            log=nhat_ky(),
            luot_hoi=[
                {"question": f"{ban_giao.NHAN_HE_THONG} sau_cv", "source": "mo_hinh"},
                {"question": f"{ban_giao.NHAN_HE_THONG} sau_matching", "source": "mo_hinh"},
                {"question": "Em nên chọn đơn nào?", "source": "khong_goi_duoc"},
            ],
        )
        self.assertNotIn(ban_giao.NHAN_HE_THONG, ban)
        self.assertNotIn("sau_cv", ban)
        self.assertIn("Em nên chọn đơn nào?", ban)

    def test_13f_api_va_ban_giao_dung_chung_mot_tien_to(self):
        """Hai nơi dùng hai tiền tố khác nhau là nhãn nội bộ lọt ra ngay."""
        import pathlib as _pl

        nguon = (
            _pl.Path(__file__).resolve().parent.parent / "app" / "api" / "agent.py"
        ).read_text(encoding="utf-8")
        self.assertIn("NHAN_HE_THONG", nguon)
        self.assertNotIn(
            '"[hệ thống] ', nguon, "api/agent.py tự viết lại tiền tố thay vì dùng chung"
        )

    def test_ban_giao_khong_goi_mo_hinh(self):
        """Nhân viên đọc rồi gọi điện cho người thật. Không dòng nào do mô hình viết."""
        import ast
        import pathlib

        nguon = (
            pathlib.Path(__file__).resolve().parent.parent
            / "app" / "agent" / "ban_giao.py"
        ).read_text(encoding="utf-8")
        cay = ast.parse(nguon)
        cam = {"app.advisor.client", "app.advisor.qa", "app.llm", "app.llm.gemini"}
        for node in ast.walk(cay):
            if isinstance(node, ast.ImportFrom) and node.module:
                self.assertNotIn(
                    node.module,
                    cam,
                    f"ban_giao.py import {node.module} — bản bàn giao phải dựng bằng mã",
                )
            elif isinstance(node, ast.Import):
                for ten in node.names:
                    self.assertNotIn(ten.name, cam)


# --- Nhóm 3: chống lạm dụng. Nội dung đi vào đây là câu hỏi của người ngoài. ---


class ChotChanDeXuatGhiTests(unittest.TestCase):
    def test_10_thong_tin_trong_chat_duoc_de_xuat_voi_nguon_chat(self):
        nhan, _ = contract.kiem_de_xuat(
            [{"field": "care_experience", "value": True, "evidence": "em từng thực tập"}],
            profile=ho_so(),
        )
        self.assertEqual(len(nhan), 1)
        self.assertEqual(nhan[0].as_dict()["source"], contract.NGUON_HOI_THOAI)

    def test_11_du_lieu_chat_khong_tu_chuyen_thanh_user_confirmed(self):
        """Mô hình khai nguồn gì cũng bị ghi đè — đây là một đường leo quyền."""
        nhan, _ = contract.kiem_de_xuat(
            [
                {
                    "field": "care_experience",
                    "value": True,
                    "source": "user_confirmed",
                }
            ],
            profile=ho_so(),
        )
        self.assertEqual(len(nhan), 1)
        self.assertEqual(nhan[0].as_dict()["source"], "chat")
        self.assertTrue(nhan[0].as_dict()["requires_confirmation"])

    def test_11b_mo_hinh_khai_nguon_staff_cung_bi_ghi_de(self):
        nhan, _ = contract.kiem_de_xuat(
            [{"field": "major", "value": "Điều dưỡng", "source": "staff"}],
            profile=ho_so(),
        )
        self.assertEqual(nhan[0].as_dict()["source"], "chat")

    def test_17_truong_ngoai_danh_sach_bi_loai(self):
        for ten in ("status", "version", "code", "session_id", "is_admin", "assigned_to"):
            nhan, loai = contract.kiem_de_xuat(
                [{"field": ten, "value": "x"}], profile=ho_so()
            )
            self.assertEqual(nhan, [], f"trường {ten!r} lọt qua chốt chặn")
            # Đòi đúng thông báo của **danh sách trường cho phép**, không nhận
            # một lời từ chối bất kỳ.
            #
            # Phá thử ngày 01/10: bỏ hẳn phép kiểm danh sách mà không ca nào đỏ,
            # vì `extra="forbid"` trên payload hồ sơ cũng từ chối những trường ấy
            # — cùng kết quả, khác tầng. Ca kiểm thử không phân biệt được hai
            # tầng thì không canh được tầng nào.
            self.assertIn(
                "không cho phép ghi",
                loai[0],
                f"{ten!r} bị loại bởi tầng khác, không bởi danh sách trường cho phép",
            )

    def test_17_hai_lop_chot_phai_trung_khit(self):
        """Payload hồ sơ và danh sách trường cho phép phải phủ đúng nhau.

        Hai tầng cùng chặn một thứ: danh sách `TRUONG_CHO_PHEP` ở Agent, và
        `extra="forbid"` trên `FieldsPayload`/`PreferencesPayload`. Hôm nay chúng
        trùng khít, nên bỏ một tầng vẫn an toàn.

        Nhưng sự trùng khít đó là **tình cờ của mã hiện tại**. Thêm một trường
        vào payload mà quên thêm vào danh sách — hoặc ngược lại — là một tầng
        lặng lẽ thôi phủ phần đó, và không có gì báo. Ca này làm chỗ lệch ấy đỏ
        ngay lúc nó xuất hiện, kèm tên trường bị lệch.
        """
        from app.api import profiles as api_profiles

        self.assertEqual(
            set(api_profiles.FieldsPayload.model_fields),
            set(profiles.FIELD_KEYS),
            "FieldsPayload lệch khỏi FIELD_KEYS — danh sách trường cho phép nay là chốt duy nhất",
        )
        self.assertEqual(
            set(api_profiles.PreferencesPayload.model_fields),
            set(profiles.PREFERENCE_KEYS),
            "PreferencesPayload lệch khỏi PREFERENCE_KEYS",
        )
        # Và cả hai phải nằm trong danh sách Agent được phép đề xuất.
        self.assertEqual(
            contract.TRUONG_CHO_PHEP,
            profiles.FIELD_KEYS | profiles.PREFERENCE_KEYS,
        )

    def test_17b_khong_de_len_du_lieu_nhan_vien_vua_chot(self):
        hs = ho_so()
        hs["fields"]["japanese_level"] = {"value": "N4", "source": "staff"}
        nhan, loai = contract.kiem_de_xuat(
            [{"field": "japanese_level", "value": "N1"}], profile=hs
        )
        self.assertEqual(nhan, [])
        self.assertIn("đáng tin hơn", loai[0])

    def test_kieu_du_lieu_sai_bi_loai_kem_ly_do_doc_duoc(self):
        nhan, loai = contract.kiem_de_xuat(
            [{"field": "birth_year", "value": "năm ngoái"}], profile=ho_so()
        )
        self.assertEqual(nhan, [])
        # Lý do phải nói được điều gì, không phải lặp lại tên trường.
        self.assertNotEqual(loai[0].strip(), "birth_year: birth_year")
        self.assertGreater(len(loai[0]), len("birth_year: ") + 8)

    def test_trung_truong_trong_mot_luot_chi_nhan_mot(self):
        nhan, loai = contract.kiem_de_xuat(
            [
                {"field": "care_experience", "value": True},
                {"field": "care_experience", "value": False},
            ],
            profile=ho_so(),
        )
        self.assertEqual(len(nhan), 1)
        self.assertTrue(any("cùng trường" in l for l in loai))

    def test_17c_hanh_dong_dang_ky_khong_duoc_mo_hinh_de_nghi(self):
        """Đăng ký tạo việc cho nhân viên gọi điện. Nó phải đến từ một cú bấm."""
        hd, loai = contract.kiem_hanh_dong({"type": "register", "label": "Đăng ký luôn"})
        self.assertIsNone(hd)
        self.assertTrue(loai)

    def test_17d_hanh_dong_bia_ra_bi_loai(self):
        for loai_hd in ("delete_profile", "run_sql", "confirm_registration", ""):
            hd, _ = contract.kiem_hanh_dong({"type": loai_hd, "label": "x"})
            self.assertIsNone(hd, f"hành động {loai_hd!r} lọt qua")


class ChotChanCauTraLoiTests(unittest.IsolatedAsyncioTestCase):
    """Chốt chặn chạy trên `reply`, và nếu `reply` bị loại thì bỏ cả đề xuất."""

    async def _chay(self, van_ban: str, *, khoi: str = "[Kết quả] N4 ứng viên N4."):
        with patch(
            "app.advisor.client.sinh_van_ban",
            AsyncMock(return_value=(van_ban, "ok", "model-thu")),
        ):
            return await orchestrator.tra_loi(
                cau_hoi="Em có hợp không?",
                profile=ho_so(),
                trang_thai=state.suy_ra(profile=ho_so()),
                khoi_doi_chieu=khoi,
            )

    async def test_reply_bia_so_thi_bi_loai_va_de_xuat_cung_bi_bo(self):
        ket, nguon, _ = await self._chay(
            '{"reply": "Chi phí của bạn là 250 triệu đồng.",'
            ' "facts_to_save": [{"field": "care_experience", "value": true}]}'
        )
        self.assertEqual(nguon, qa.NGUON_KHONG_BIET)
        self.assertEqual(ket.reply, qa.CAU_KHONG_BIET)
        # Phần cấu trúc đến từ cùng một lượt sinh — tin nó là không có căn cứ.
        self.assertEqual(ket.de_xuat, ())

    async def test_reply_hua_hen_thi_bi_loai(self):
        ket, nguon, _ = await self._chay(
            '{"reply": "Bạn chắc chắn sẽ đỗ đơn này, yên tâm nhé."}'
        )
        self.assertEqual(nguon, qa.NGUON_KHONG_BIET)

    async def test_reply_cau_do_thi_bi_loai(self):
        ket, nguon, _ = await self._chay('{"reply": "Về điều kiện sức khỏe của"}')
        self.assertEqual(nguon, qa.NGUON_KHONG_BIET)

    async def test_14_mo_hinh_khong_goi_duoc_thi_van_co_duong_di_tiep(self):
        with patch(
            "app.advisor.client.sinh_van_ban",
            AsyncMock(return_value=(None, "khong_goi_duoc", "model-thu")),
        ):
            ket, nguon, _ = await orchestrator.tra_loi(
                cau_hoi="Em có hợp không?",
                profile=ho_so(),
                trang_thai=state.suy_ra(profile=ho_so()),
                khoi_doi_chieu="",
            )
        self.assertEqual(nguon, qa.NGUON_KHONG_GOI_DUOC)
        self.assertEqual(ket.reply, qa.CAU_KHONG_GOI_DUOC)
        self.assertEqual(ket.de_xuat, ())

    async def test_khong_boc_duoc_json_thi_dung_ca_cau_lam_reply(self):
        """Mô hình phớt lờ định dạng. Mất phần cấu trúc, không mất lượt."""
        ket, nguon, _ = await self._chay(
            "Hồ sơ của bạn đạt điều kiện tiếng Nhật N4 của đơn này."
        )
        self.assertEqual(nguon, qa.NGUON_MO_HINH)
        self.assertIn("N4", ket.reply)

    async def test_json_boc_trong_dau_nhay_ba_van_doc_duoc(self):
        ket, nguon, _ = await self._chay(
            '```json\n{"reply": "Hồ sơ của bạn đạt điều kiện N4."}\n```'
        )
        self.assertEqual(nguon, qa.NGUON_MO_HINH)
        self.assertEqual(ket.reply, "Hồ sơ của bạn đạt điều kiện N4.")

    async def test_bo_nho_khong_nam_trong_khoi_cho_phep(self):
        """Một con số lọt vào bộ nhớ chung cũng không được đi ra ngoài."""
        with patch(
            "app.advisor.client.sinh_van_ban",
            AsyncMock(return_value=('{"reply": "Chi phí là 123 triệu."}', "ok", "m")),
        ):
            _ket, nguon, _ = await orchestrator.tra_loi(
                cau_hoi="Chi phí bao nhiêu?",
                profile=ho_so(),
                trang_thai=state.suy_ra(profile=ho_so()),
                khoi_doi_chieu="",
                bo_nho={
                    "moi_quan_tam": [
                        {"chu_de": "chi_phi", "so_lan": 3, "cau_gan_nhat": "123 triệu à?"}
                    ]
                },
            )
        self.assertEqual(nguon, qa.NGUON_KHONG_BIET)


class CachLyPhienTests(unittest.TestCase):
    """Ca 16: cookie của phiên này không mở được hồ sơ của phiên khác."""

    def setUp(self):
        app = FastAPI()
        app.include_router(public_router)
        self.client = TestClient(app)

    def test_16_khong_cookie_thi_khong_vao_duoc(self):
        for duong in (
            f"/tu-van/v1/{PHIEN}/tro-ly",
            f"/tu-van/v1/{PHIEN}/tro-ly/hoi",
            f"/tu-van/v1/{PHIEN}/tro-ly/ban-giao",
        ):
            ra = self.client.get(duong)
            self.assertIn(ra.status_code, (401, 403), f"{duong} vào được mà không cookie")

    def test_16b_cookie_cua_minh_khong_mo_duoc_phien_khac(self):
        ra = self.client.get(
            f"/tu-van/v1/{PHIEN_KHAC}/tro-ly", cookies=cookies_cho(PHIEN)
        )
        self.assertIn(ra.status_code, (401, 403))

    def test_18_khong_tra_ve_truong_noi_bo(self):
        """Ca 18: không đưa dữ liệu không phận sự xuống trình duyệt."""
        with patch(
            "app.db.candidate_profiles.get_by_session", AsyncMock(return_value=None)
        ), patch(
            "app.db.session_memory.lay", AsyncMock(return_value=None)
        ), patch(
            "app.db.support_requests.list_for_session", AsyncMock(return_value=[])
        ), patch(
            # Vá ở `app.api.agent`, không ở `app.db.database`: module kia đã
            # `from ... import` nên tên được gắn vào không gian của chính nó, và
            # vá chỗ gốc không đổi được thứ nó đang giữ.
            "app.api.agent.list_unassigned_registrations", AsyncMock(return_value=[])
        ), patch.object(
            advisor_turns, "list_turns", AsyncMock(return_value=[])
        ):
            ra = self.client.get(
                f"/tu-van/v1/{PHIEN}/tro-ly", cookies=cookies_cho(PHIEN)
            )
        self.assertEqual(ra.status_code, 200)
        chu = ra.text
        for cam in ("internal_note", "created_by", "assigned_to", "_id"):
            self.assertNotIn(cam, chu, f"phản hồi chứa trường nội bộ {cam!r}")


class KhongTuXacNhanHoSoTests(unittest.TestCase):
    """Ca 17: không đường nào để mô hình tự xác nhận hồ sơ hay đăng ký đơn."""

    def test_duong_xac_nhan_khong_doi_trang_thai_ho_so(self):
        import ast
        import pathlib

        nguon = (
            pathlib.Path(__file__).resolve().parent.parent
            / "app" / "api" / "agent.py"
        ).read_text(encoding="utf-8")
        cay = ast.parse(nguon)
        ham = next(
            n
            for n in ast.walk(cay)
            if isinstance(n, ast.AsyncFunctionDef) and n.name == "_ghi_mot_truong"
        )
        # `status=None` nghĩa là không đụng tới trạng thái. Bất cứ giá trị khác
        # là một đường nhảy tắt sang hồ sơ đã xác nhận.
        for node in ast.walk(ham):
            if isinstance(node, ast.keyword) and node.arg == "status":
                self.assertIsInstance(
                    node.value,
                    ast.Constant,
                    "status phải là hằng None, không phải biểu thức",
                )
                self.assertIsNone(
                    node.value.value,
                    "đường xác nhận một trường không được đổi trạng thái hồ sơ",
                )
                break
        else:
            self.fail("không thấy tham số status trong _ghi_mot_truong")

    def test_than_yeu_cau_xac_nhan_khong_nhan_truong_source(self):
        """Nhận `source` từ trình duyệt là mở sẵn một đường leo quyền."""
        from app.api.agent import XacNhanBody

        self.assertNotIn("source", XacNhanBody.model_fields)
        self.assertEqual(XacNhanBody.model_config.get("extra"), "forbid")


if __name__ == "__main__":
    unittest.main()


class BanGiaoDiKemYeuCauHoTroTests(unittest.IsolatedAsyncioTestCase):
    """Ca 13: chuyển nhân viên thì bản tóm tắt phải đi cùng.

    Và quan trọng không kém: **phần tóm tắt hỏng không được làm mất yêu cầu**.
    Khách vừa bấm "xin gặp nhân viên" sau khi đọc một kết quả nói họ chưa đủ điều
    kiện — để lời gọi ấy trả lỗi vì phần tóm tắt trục trặc là chặn đúng người
    đang cần giúp nhất.
    """

    async def test_13c_yeu_cau_ho_tro_mang_theo_ban_giao(self):
        from app.api import support

        da_luu: dict = {}

        async def _tao(document):
            da_luu.update(document)
            return document, True

        with patch.object(support.store, "create_request", _tao), patch.object(
            support, "_bao_nhan_vien", AsyncMock()
        ), patch.object(
            support.khoi_doi_chieu, "dung_tu_nhat_ky", AsyncMock(return_value=None)
        ), patch(
            "app.api.agent._nap",
            AsyncMock(
                return_value=(ho_so(), state.suy_ra(profile=ho_so()), nhat_ky())
            ),
        ), patch.object(
            advisor_turns, "list_all_turns", AsyncMock(return_value=[])
        ), patch(
            "app.api.support.list_appointments_for_session",
            AsyncMock(return_value=[]),
        ):
            await support.gui_yeu_cau(
                PHIEN,
                support.SupportRequestBody(
                    kind="gap_mat",
                    full_name="Trần Thị Thu Hà",
                    phone="0914552780",
                    message="Em muốn gặp trực tuyến.",
                ),
                _yeu_cau_gia(),
            )

        self.assertIn("ban_giao", da_luu)
        ban = da_luu["ban_giao"]
        # Thân bản KHÔNG mang dòng tiêu đề: nơi hiển thị đã có nhãn riêng,
        # và thêm vào đây là hai dòng tiêu đề liền nhau trên màn hình.
        self.assertNotIn("TÓM TẮT BÀN GIAO", ban)
        self.assertTrue(ban.startswith("TÌNH TRẠNG:"))
        self.assertIn("VIỆC NÊN LÀM TIẾP", ban)
        # Lời nhắn riêng của khách phải nằm trong đó, không bị bản ghép đè mất.
        self.assertIn("Em muốn gặp trực tuyến.", ban)

    async def test_13d_dung_ban_giao_hong_khong_lam_mat_yeu_cau(self):
        from app.api import support

        da_luu: dict = {}

        async def _tao(document):
            da_luu.update(document)
            return document, True

        with patch.object(support.store, "create_request", _tao), patch.object(
            support, "_bao_nhan_vien", AsyncMock()
        ), patch.object(
            support.khoi_doi_chieu, "dung_tu_nhat_ky", AsyncMock(return_value=None)
        ), patch(
            "app.api.agent._nap", AsyncMock(side_effect=RuntimeError("database sập"))
        ):
            ra = await support.gui_yeu_cau(
                PHIEN,
                support.SupportRequestBody(
                    kind="nhan_tin", full_name="Nguyễn Văn A", phone="0912345678"
                ),
                _yeu_cau_gia(),
            )

        # Yêu cầu vẫn được tạo, chỉ thiếu phần tóm tắt.
        self.assertTrue(da_luu.get("code"))
        self.assertIsNone(da_luu.get("ban_giao"))
        self.assertTrue(ra)


_IP_GIA = iter(range(1, 1 << 24))


def _yeu_cau_gia():
    """`Request` tối thiểu đủ cho bộ giới hạn theo IP đọc địa chỉ.

    **Mỗi lần gọi một IP riêng.** Bộ giới hạn tần suất là một đối tượng dùng chung
    trong tiến trình, nên mọi ca trong module chia nhau cùng một hạn mức nếu cùng
    IP. Bản trước dùng cố định `127.0.0.1`: đường gửi yêu cầu hỗ trợ cho 5 lượt /
    10 phút, và ngày 06/10 ca thứ sáu được thêm vào module làm một ca KHÁC nhận
    429 — đỏ hay xanh tùy số ca đứng trước nó. Một IP mỗi lần gọi thì mỗi ca có
    hạn mức của riêng mình, đúng như hai khách thật.
    """
    from starlette.requests import Request

    n = next(_IP_GIA)
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/",
            "headers": [],
            "client": (f"10.{n >> 16 & 255}.{n >> 8 & 255}.{n & 255}", 1234),
            "query_string": b"",
        }
    )


class LoiGanLichKhongLamGayYeuCauTests(unittest.IsolatedAsyncioTestCase):
    """Gắn lịch vào yêu cầu hỏng thì **không được** làm gãy lời gọi của khách.

    ## Tình huống tái hiện được

    Khách bấm "Xin gặp mặt" kèm khung giờ. Máy chủ tạo yêu cầu hỗ trợ, tạo lịch
    hẹn, rồi gọi `gan_lich_hen()` để ghi mã lịch vào yêu cầu. Lời gọi thứ ba gặp
    lỗi database.

    Trước 06/10 nó không có chốt chặn, nên hậu quả là ba thứ cùng lúc:

    1. Lời gọi API văng lỗi → màn hình khách báo gửi thất bại.
    2. `_bao_nhan_vien` nằm **sau** nó nên không chạy → **không ai được thông báo**.
    3. Nhưng yêu cầu **và** lịch hẹn đều đã nằm trong database.

    Khách thấy "chưa gửi được" nên bấm lại, và lần bấm thứ hai bị index duy nhất
    chặn — đúng về dữ liệu, nhưng khách vẫn không biết mình đã gửi được hay chưa.
    Trong khi nhân viên thì không hề biết có người đang chờ gọi lại.

    ## Vì sao mất trường ấy không mất liên kết

    Liên kết ghi **hai chiều, ở hai bản ghi**: `support_code` trên bản ghi lịch
    (ghi ngay lúc tạo lịch) và `appointment_code` trên yêu cầu. Bước hỏng chỉ làm
    mất chiều thứ hai, nên `store.lay_lich_hen_lien_quan()` lần ngược được từ
    phía lịch và tự gắn lại khi nhân viên mở yêu cầu.
    """

    async def _gui(self, *, gan_lich_loi: bool):
        from app.api import support

        da_luu: dict = {}
        da_bao: list = []

        async def _tao(document):
            da_luu.update(document)
            return document, True

        async def _gan(*a, **kw):
            raise RuntimeError("database chớp một nhịp")

        async def _bao(document, kind):
            da_bao.append((document.get("code"), kind))

        async def _tao_lich(*a, **kw):
            return "TV-20261010-AAAA"

        with patch.object(support.store, "create_request", _tao), patch.object(
            support, "_bao_nhan_vien", _bao
        ), patch.object(
            support.khoi_doi_chieu, "dung_tu_nhat_ky", AsyncMock(return_value=None)
        ), patch.object(
            support, "_tao_lich_hen", _tao_lich
        ), patch.object(
            support, "_ban_giao", AsyncMock(return_value="TÌNH TRẠNG: …")
        ), patch.object(
            support.store,
            "gan_lich_hen",
            _gan if gan_lich_loi else AsyncMock(return_value=None),
        ):
            ra = await support.gui_yeu_cau(
                PHIEN,
                support.SupportRequestBody(
                    kind="gap_mat",
                    full_name="Trần Thị Thu Hà",
                    phone="0914552780",
                    message="Em muốn gặp trực tiếp.",
                    appointment_date=(local_today() + timedelta(days=3)).isoformat(),
                    appointment_time="14:00",
                    meeting_kind="truc_tiep",
                ),
                _yeu_cau_gia(),
            )
        return ra, da_luu, da_bao

    async def test_gan_lich_loi_van_tra_ve_201_va_mang_ma_lich(self):
        ra, da_luu, _bao = await self._gui(gan_lich_loi=True)
        # Lịch ĐÃ được tạo, nên vẫn phải nói cho khách biết. Im lặng ở đây là để
        # khách tưởng khung giờ mình chọn không được ghi nhận.
        self.assertEqual(ra.get("appointment_code"), "TV-20261010-AAAA")
        self.assertTrue(da_luu.get("code"))

    async def test_gan_lich_loi_van_bao_nhan_vien(self):
        """Điểm nặng nhất: không ai được thông báo là không ai gọi lại."""
        _ra, da_luu, da_bao = await self._gui(gan_lich_loi=True)
        self.assertEqual(len(da_bao), 1, "nhân viên không được thông báo")
        self.assertEqual(da_bao[0], (da_luu["code"], "gap_mat"))

    async def test_duong_binh_thuong_khong_doi(self):
        """Đối chứng: không có lỗi thì mọi thứ vẫn như cũ."""
        ra, da_luu, da_bao = await self._gui(gan_lich_loi=False)
        self.assertEqual(ra.get("appointment_code"), "TV-20261010-AAAA")
        self.assertEqual(len(da_bao), 1)
        self.assertTrue(da_luu.get("ban_giao"))


class BamLaiThiNhanLaiDungLichCuTests(unittest.IsolatedAsyncioTestCase):
    """Bấm lại sau một lần lỗi: khách phải thấy lịch **đã có**, không phải dòng vàng.

    Đường đi tệ nhất trước 06/10: lần bấm đầu tạo được lịch nhưng lời gọi lỗi ở
    bước sau, khách bấm lại, index `booking_key` chặn lịch thứ hai, `_tao_lich_hen`
    trả `None` — và màn hình hiện *"Khung giờ bạn chọn chưa thành lịch hẹn"*.
    Lịch thì có thật; chỉ có khách là bị nói điều ngược lại.
    """

    def _body(self):
        from app.api import support

        return support.SupportRequestBody(
            kind="gap_mat",
            full_name="Trần Thị Thu Hà",
            phone="0914552780",
            appointment_date=(local_today() + timedelta(days=3)).isoformat(),
            appointment_time="14:00",
            meeting_kind="truc_tiep",
        )

    async def test_trung_khoa_thi_tra_ma_lich_da_co(self):
        from pymongo.errors import DuplicateKeyError

        from app.api import support

        with patch(
            "app.db.database.create_appointment",
            AsyncMock(side_effect=DuplicateKeyError("trùng booking_key")),
        ), patch.object(
            support,
            "_lich_theo_khoa",
            AsyncMock(return_value={"appointment_code": "TV-20261010-CUUU"}),
        ):
            ma = await support._tao_lich_hen(PHIEN, self._body(), "HT-111111")
        self.assertEqual(ma, "TV-20261010-CUUU")

    async def test_tra_theo_dung_khoa_chong_trung(self):
        """Tra bằng đúng khóa đã bị chặn — không tra theo phiên hay theo tên."""
        from pymongo.errors import DuplicateKeyError

        from app.api import support

        tra = AsyncMock(return_value={"appointment_code": "TV-X"})
        with patch(
            "app.db.database.create_appointment",
            AsyncMock(side_effect=DuplicateKeyError("trùng")),
        ), patch.object(support, "_lich_theo_khoa", tra):
            await support._tao_lich_hen(PHIEN, self._body(), "HT-111111")
        khoa = tra.await_args.args[0]
        self.assertTrue(khoa.startswith("0914552780|"))
        self.assertTrue(khoa.endswith("|14:00"))

    async def test_tra_khoa_cung_hong_thi_van_khong_nem_loi(self):
        """Database hỏng cả ở bước tra lại: vẫn không làm gãy yêu cầu hỗ trợ."""
        from pymongo.errors import DuplicateKeyError

        from app.api import support

        with patch(
            "app.db.database.create_appointment",
            AsyncMock(side_effect=DuplicateKeyError("trùng")),
        ), patch.object(support, "_lich_theo_khoa", AsyncMock(return_value=None)):
            ma = await support._tao_lich_hen(PHIEN, self._body(), "HT-111111")
        self.assertIsNone(ma)


class _BoSuuTapGia:
    """Một collection Mongo trong bộ nhớ, đủ cho đường hỗ trợ: tìm, ghi, nhận.

    Khớp điều kiện bằng so bằng từng khóa — đúng những gì `support_requests`
    dùng. Không mô phỏng toán tử nào khác, để ca kiểm thử không vô tình dựa vào
    một hành vi mà Mongo thật không có.
    """

    def __init__(self, ban_ghi=()):
        self.ds = [dict(b) for b in ban_ghi]
        self.so_lan_ghi = 0

    def _khop(self, b, dk):
        return all(b.get(k) == v for k, v in dk.items())

    async def find_one(self, dk, proj=None, *, sort=None):
        khop = [b for b in self.ds if self._khop(b, dk)]
        # Mô phỏng ĐÚNG `sort` của Mongo cho một khóa. Bỏ qua nó thì một ca kiểm
        # thứ tự sẽ xanh vì thứ tự chèn tình cờ trùng thứ tự mong muốn.
        for khoa, chieu in reversed(sort or []):
            khop.sort(key=lambda b: b.get(khoa), reverse=chieu < 0)
        return dict(khop[0]) if khop else None

    async def update_one(self, dk, doi):
        self.so_lan_ghi += 1
        for b in self.ds:
            if self._khop(b, dk):
                b.update(doi.get("$set") or {})
                return

    async def find_one_and_update(self, dk, doi, projection=None, return_document=None):
        for b in self.ds:
            if self._khop(b, dk):
                b.update(doi.get("$set") or {})
                return dict(b)
        return None


class _DbGia:
    def __init__(self, yeu_cau, lich):
        self.yeu_cau = _BoSuuTapGia(yeu_cau)
        self.consultation_appointments = _BoSuuTapGia(lich)

    def __getitem__(self, _ten):
        return self.yeu_cau


class KhoiPhucBanGiaoTheoMoiThuTuTests(unittest.IsolatedAsyncioTestCase):
    """Gắn lịch hỏng lúc tạo → nhân viên phải thấy giờ hẹn, **bấm theo thứ tự nào cũng vậy**.

    ## Lỗi chủ đồ án tái hiện được ngày 06/10

    Bản sửa đầu có hai đường khôi phục: mở chi tiết thì gắn lại liên kết **và**
    dựng lại bàn giao; nhận xử lý thì **chỉ** gắn lại liên kết. Đường mở chi tiết
    lại quyết định có dựng lại hay không bằng cách nhìn `appointment_code` có
    trống không.

    Nên bấm "nhận xử lý" trước thì: đường nhận gắn lại `appointment_code` → đường
    mở chi tiết thấy trường đã có → không dựng lại → bản bàn giao thiếu giờ hẹn
    **mãi mãi**. Chính bước sửa của đường này xóa mất dấu hiệu của đường kia.

    ## Cách sửa

    Một hàm `_dong_bo_lich` cho mọi đường, và tín hiệu trực tiếp `ban_giao_lich`:
    bản bàn giao đã lưu được dựng với lịch nào.
    """

    YEU_CAU = {
        "code": "HT-AAAAAA",
        "session_id": PHIEN,
        "message": "Em muốn gặp.",
        "status": "cho_xu_ly",
        "assigned_to": None,
        # Trạng thái sau khi gắn lịch HỎNG lúc tạo: có bàn giao cũ, không có
        # mã lịch, không có dấu `ban_giao_lich`.
        "ban_giao": "TÌNH TRẠNG: …\nVIỆC NÊN LÀM TIẾP\n  Gọi lại",
    }
    LICH = {
        "appointment_code": "TV-20261010-BBBB",
        "support_code": "HT-AAAAAA",
        "appointment_date": "2026-10-10",
        "appointment_time": "14:00",
    }
    BAN_MOI = "TÌNH TRẠNG: …\nKHÁCH ĐÃ CHỌN KHUNG GIỜ\n  14:00 ngày 10/10/2026"

    async def _chay(self, thu_tu, *, dung_hong=False):
        from app.api import support
        from app.db import support_requests as store

        db = _DbGia([self.YEU_CAU], [self.LICH])
        dung = AsyncMock(return_value=None if dung_hong else self.BAN_MOI)
        nguoi = {"email": "a@local.test", "role": "consultant"}
        with patch.object(store, "get_db", lambda: db), patch.object(
            support, "_ban_giao", dung
        ), patch.object(support, "audit_action", AsyncMock()):
            for buoc in thu_tu:
                if buoc == "nhan":
                    await support.nhan_xu_ly("HT-AAAAAA", _yeu_cau_gia(), current_user=nguoi)
                else:
                    await support.chi_tiet("HT-AAAAAA", current_user=nguoi)
        return db.yeu_cau.ds[0], dung

    async def test_nhan_truoc_roi_mo_chi_tiet_van_co_gio_hen(self):
        """Đúng thứ tự chủ đồ án dùng để tái hiện."""
        sau, _ = await self._chay(["nhan", "mo"])
        self.assertEqual(sau["appointment_code"], "TV-20261010-BBBB")
        self.assertIn("14:00", sau["ban_giao"], "bàn giao vẫn thiếu giờ hẹn")
        self.assertEqual(sau["ban_giao_lich"], "TV-20261010-BBBB")

    async def test_chi_nhan_xu_ly_thoi_cung_du(self):
        """Nhân viên có thể nhận rồi gọi luôn, không bao giờ mở trang chi tiết."""
        sau, _ = await self._chay(["nhan"])
        self.assertIn("14:00", sau["ban_giao"])

    async def test_mo_truoc_roi_nhan(self):
        sau, _ = await self._chay(["mo", "nhan"])
        self.assertIn("14:00", sau["ban_giao"])

    async def test_sua_xong_thi_khong_dung_lai_nua(self):
        """Đọc không được biến thành ghi mỗi lần mở khi chẳng còn gì cần sửa."""
        _sau, dung = await self._chay(["nhan", "mo", "mo", "mo"])
        self.assertEqual(dung.await_count, 1)

    async def test_dung_hong_thi_lan_mo_sau_thu_lai(self):
        """Dựng hỏng: vẫn gắn liên kết, nhưng KHÔNG đánh dấu đã có lịch."""
        sau, dung = await self._chay(["nhan", "mo"], dung_hong=True)
        self.assertEqual(sau["appointment_code"], "TV-20261010-BBBB")
        self.assertNotIn("ban_giao_lich", sau)
        # Dấu hiệu còn lệch nên mỗi lần mở đều thử lại — không im lặng bỏ cuộc.
        self.assertEqual(dung.await_count, 2)

    async def test_yeu_cau_khong_co_lich_thi_khong_ghi_gi(self):
        from app.api import support
        from app.db import support_requests as store

        db = _DbGia([{**self.YEU_CAU, "code": "HT-CCCCCC"}], [])
        with patch.object(store, "get_db", lambda: db), patch.object(
            support, "_ban_giao", AsyncMock()
        ):
            ra = await support.chi_tiet("HT-CCCCCC", current_user={"email": "a"})
        self.assertIsNone(ra["appointment"])
        self.assertEqual(db.yeu_cau.so_lan_ghi, 0)


class LichMoiNhatTests(unittest.IsolatedAsyncioTestCase):
    """Khách gửi lại với khung giờ khác: yêu cầu gộp, lịch thứ hai vẫn tạo.

    Nhân viên phải thấy lịch MỚI NHẤT — đúng mã khách vừa được báo — chứ không
    phải lịch nào `find_one` tình cờ gặp trước.
    """

    async def test_tra_lich_moi_nhat_bat_ke_thu_tu_chen(self):
        from datetime import datetime, timezone

        from app.db import support_requests as store

        cu = {"appointment_code": "TV-CU", "support_code": "HT-1",
              "created_at": datetime(2026, 10, 6, 1, tzinfo=timezone.utc)}
        moi = {"appointment_code": "TV-MOI", "support_code": "HT-1",
               "created_at": datetime(2026, 10, 6, 2, tzinfo=timezone.utc)}
        for thu_tu in ([cu, moi], [moi, cu]):
            with self.subTest(chen_truoc=thu_tu[0]["appointment_code"]):
                db = _DbGia([{"code": "HT-1"}], thu_tu)
                with patch.object(store, "get_db", lambda: db):
                    lich = await store.lay_lich_hen_lien_quan("HT-1")
                self.assertEqual(lich["appointment_code"], "TV-MOI")


class KhoiDoiChieuHongKhongMatYeuCauTests(unittest.IsolatedAsyncioTestCase):
    """Khối đối chiếu dựng TRƯỚC khi tạo yêu cầu — hỏng ở đó không được làm mất yêu cầu."""

    async def test_khoi_doi_chieu_nem_loi_van_tao_yeu_cau(self):
        from app.api import support

        da_luu: dict = {}

        async def _tao(document):
            da_luu.update(document)
            return document, True

        with patch.object(support.store, "create_request", _tao), patch.object(
            support, "_bao_nhan_vien", AsyncMock()
        ), patch.object(
            support.khoi_doi_chieu,
            "dung_tu_nhat_ky",
            AsyncMock(side_effect=RuntimeError("database chớp một nhịp")),
        ), patch.object(support, "_ban_giao", AsyncMock(return_value="TÌNH TRẠNG: …")):
            ra = await support.gui_yeu_cau(
                PHIEN,
                support.SupportRequestBody(
                    kind="nhan_tin", full_name="Nguyễn Văn A", phone="0912345678"
                ),
                _yeu_cau_gia(),
            )
        self.assertTrue(da_luu.get("code"), "yêu cầu không được tạo")
        self.assertIsNone(da_luu.get("advice_block"))
        self.assertTrue(ra)


class TinHieuDungLaiBanGiaoTests(unittest.TestCase):
    def test_bon_truong_hop(self):
        from app.db.support_requests import can_dung_lai_ban_giao as can

        lich = {"appointment_code": "TV-1"}
        self.assertTrue(can({}, lich), "chưa từng dựng với lịch nào")
        self.assertTrue(can({"ban_giao_lich": "TV-0"}, lich), "dựng với lịch khác")
        self.assertFalse(can({"ban_giao_lich": "TV-1"}, lich), "đã đúng lịch")
        self.assertFalse(can({}, None), "không có lịch thì không có gì để dựng")


class HetHanMucVanKhongMatGiTests(unittest.IsolatedAsyncioTestCase):
    """Ca 5: AI hết hạn mức — hệ thống phải còn dùng được, không mất gì.

    ## Vì sao đây là ca nghiệm thu, không phải tình huống ngoại lệ

    Gói Gemini miễn phí cho **20 lượt mỗi ngày trên mỗi dự án và mỗi model**, và
    hạn mức ấy dùng chung giữa đo chất lượng và chạy thật. Hết hạn mức là trạng
    thái vận hành **bình thường**, không phải sự cố. Nên câu "hệ thống còn gì khi
    AI im" phải có câu trả lời đo được.

    Ca này không giả lập một lỗi mạng. Nó tắt `ADVISOR_ENABLED` — đúng đường mà
    `client.sinh_van_ban` đi khi hết hạn mức, vì cả hai nhánh đều trả `None`.

    ## Ba thứ phải còn nguyên

    1. Lời gọi **không nổ**: khách nhận một câu nói rõ tình trạng, không phải 500.
    2. **Lượt vẫn được ghi**: `add_turn` nằm sau lời gọi mô hình và không có điều
       kiện nào. Nếu nó nằm trong nhánh thành công thì câu khách vừa hỏi biến mất
       — và nhân viên đọc bàn giao sẽ không biết họ đã hỏi gì.
    3. **Bàn giao nêu đúng rằng trợ lý chưa trả lời được**, để nhân viên biết
       phải gọi lại. Một bản bàn giao chép lại câu "đang bận" như thể đó là nội
       dung tư vấn thì tệ hơn là không có.
    """

    async def _hoi_khi_tat_ai(self):
        from app.api import agent as agent_api
        from app.core.config import settings

        da_ghi: list[dict] = []

        async def _add_turn(**kw):
            da_ghi.append(kw)
            return None

        goc = settings.advisor_enabled
        settings.advisor_enabled = False
        try:
            with patch(
                "app.api.agent._nap",
                AsyncMock(
                    return_value=(ho_so(), state.suy_ra(profile=ho_so()), nhat_ky())
                ),
            ), patch.object(
                advisor_turns, "count_turns", AsyncMock(return_value=0)
            ), patch.object(
                advisor_turns, "list_turns", AsyncMock(return_value=[])
            ), patch.object(
                advisor_turns, "add_turn", _add_turn
            ), patch(
                "app.api.agent.session_memory.lay", AsyncMock(return_value={})
            ), patch.object(
                agent_api, "_ghi_moc", AsyncMock()
            ), patch.object(
                # Dựng lại khối đối chiếu từ nhật ký là việc của ca khác.
                # Ca này đo đúng một thứ: đường đi khi mô hình không trả lời.
                agent_api,
                "_khoi_doi_chieu",
                lambda _log: "[Kết quả] đơn DH-0001 · tiếng Nhật N4 → ĐẠT",
            ):
                ra = await agent_api.hoi_tro_ly(
                    PHIEN,
                    agent_api.CauHoiBody(question="Em có hợp đơn Tokyo không ạ?"),
                    _yeu_cau_gia(),
                )
        finally:
            settings.advisor_enabled = goc
        return ra, da_ghi

    async def test_tat_ai_van_tra_loi_chu_khong_tra_loi_500(self):
        ra, _ = await self._hoi_khi_tat_ai()
        self.assertEqual(ra["answer"], qa.CAU_KHONG_GOI_DUOC)
        # Nguồn phải tách riêng khỏi `khong_biet`: `advisor_turns.thong_ke()`
        # đếm `khong_biet` để trả lời "bot bí bao nhiêu lần" và **không** tính
        # `khong_goi_duoc` vào mẫu số. Gộp hai thứ vào một thì một ngày hết hạn
        # mức bị đọc thành một ngày bot kém — số liệu ấy sẽ vào báo cáo.
        #
        # So với **chuỗi chữ**, không so với chính hằng số.
        #
        # Bản đầu viết `assertEqual(ra["source"], qa.NGUON_KHONG_GOI_DUOC)`, tức
        # so hằng số với chính nó: đổi hằng số thành `"khong_biet"` thì ca vẫn
        # xanh. Đột biến ngày 05/10 lọt qua đúng chỗ này.
        self.assertEqual(ra.get("source"), "khong_goi_duoc")
        self.assertNotEqual(
            qa.NGUON_KHONG_GOI_DUOC,
            qa.NGUON_KHONG_BIET,
            "hai nguồn bị gộp — thống kê sẽ tính hết hạn mức thành bot bí",
        )
        self.assertEqual(
            advisor_turns.SOURCE_KHONG_GOI_DUOC, qa.NGUON_KHONG_GOI_DUOC,
            "tầng ghi và tầng sinh câu dùng hai tên khác nhau cho cùng một việc",
        )

    async def test_tat_ai_van_ghi_lai_cau_khach_vua_hoi(self):
        _ra, da_ghi = await self._hoi_khi_tat_ai()
        self.assertEqual(len(da_ghi), 1, "lượt không được ghi khi AI im")
        self.assertEqual(da_ghi[0]["question"], "Em có hợp đơn Tokyo không ạ?")
        self.assertEqual(da_ghi[0]["source"], "khong_goi_duoc")

    def test_ban_giao_noi_ro_tro_ly_chua_tra_loi_duoc(self):
        """Nhân viên phải thấy câu khách hỏi KÈM dấu hiệu chưa ai trả lời."""
        ban = ban_giao.dung(
            profile=ho_so(),
            trang_thai=state.suy_ra(profile=ho_so()),
            log=nhat_ky(),
            luot_hoi=[
                {
                    "question": "Em có hợp đơn Tokyo không ạ?",
                    "answer": qa.CAU_KHONG_GOI_DUOC,
                    "source": qa.NGUON_KHONG_GOI_DUOC,
                }
            ],
        )
        self.assertIn("Em có hợp đơn Tokyo không ạ?", ban)
        self.assertIn("TRỢ LÝ CHƯA TRẢ LỜI ĐƯỢC", ban)
        # Và KHÔNG chép câu "đang bận" vào bản bàn giao như thể đó là nội dung
        # tư vấn — nhân viên cần biết câu hỏi, không cần đọc lời xin lỗi.
        self.assertNotIn("đang bận", ban)


class SuaDuLieuCvTests(unittest.IsolatedAsyncioTestCase):
    """Ca 4: ứng viên sửa dữ liệu máy đọc từ CV.

    Đường xác nhận ghi nguồn `user_confirmed`, nên theo thứ tự ưu tiên nguồn nó
    **đè lên** giá trị `cv`. Đó là đúng: người vừa đọc giá trị trên màn hình và
    nói nó sai thì họ đáng tin hơn máy đọc.
    """

    async def test_4_gia_tri_nguoi_xac_nhan_de_len_gia_tri_doc_tu_cv(self):
        from app.api import agent as api_agent

        hs = ho_so()
        hs["fields"]["japanese_level"] = {"value": "N4", "source": "cv"}
        da_ghi: dict = {}

        async def _ap(session_id, **kw):
            da_ghi.update(kw)
            return {**hs, "version": 2}

        with patch.object(
            profiles, "get_by_session", AsyncMock(return_value=hs)
        ), patch.object(profiles, "apply_changes", _ap):
            await api_agent.xac_nhan_de_xuat(
                PHIEN, api_agent.XacNhanBody(field="japanese_level", value="N3")
            )

        o = da_ghi["fields"]["japanese_level"]
        self.assertEqual(o["value"], "N3")
        self.assertEqual(o["source"], "user_confirmed")
        # Và KHÔNG được chạm trạng thái hồ sơ: xác nhận một trường lẻ không phải
        # là xác nhận cả hồ sơ.
        self.assertIsNone(da_ghi["status"])

    async def test_4b_sua_dong_thoi_o_hai_noi_thi_bao_409(self):
        """Phiên bản hồ sơ lệch nghĩa là có người vừa sửa. Không ghi đè im lặng."""
        from fastapi import HTTPException

        from app.api import agent as api_agent

        with patch.object(
            profiles, "get_by_session", AsyncMock(return_value=ho_so())
        ), patch.object(profiles, "apply_changes", AsyncMock(return_value=None)):
            with self.assertRaises(HTTPException) as ctx:
                await api_agent.xac_nhan_de_xuat(
                    PHIEN, api_agent.XacNhanBody(field="gender", value="nu")
                )
        self.assertEqual(ctx.exception.status_code, 409)


class DatabaseLoiKhongMatHoiThoaiTests(unittest.IsolatedAsyncioTestCase):
    """Ca 15: database trục trặc không được làm mất cả cuộc trò chuyện.

    Phân biệt hai thứ:
    - **Ghi mốc vào bộ nhớ phiên** là phần thêm vào. Hỏng thì nuốt lỗi, vì lượt
      tư vấn đã trả lời xong và đã lưu — ném lỗi ra lúc này là xoá một câu trả
      lời đúng khỏi màn hình của người đang đọc.
    - **Ghi lượt hỏi đáp** thì không nuốt: nếu không lưu được thì người dùng phải
      biết, chứ không phải tải lại trang rồi thấy cuộc trò chuyện biến mất mà
      không hiểu vì sao.
    """

    async def test_15_bo_nho_phien_hong_khong_lam_mat_luot_tu_van(self):
        from app.api import agent as api_agent

        with patch(
            "app.db.session_memory.ghi_moc_tu_van",
            AsyncMock(side_effect=RuntimeError("mất kết nối")),
        ):
            # Không ném ra ngoài.
            await api_agent._ghi_moc(PHIEN, state.suy_ra(profile=ho_so()))

    async def test_15b_ghi_moc_hong_duoc_ghi_lai_vao_log(self):
        """Nuốt lỗi mà không ghi log là làm mất dấu vết của một sự cố thật."""
        from app.api import agent as api_agent

        with patch(
            "app.db.session_memory.ghi_moc_tu_van",
            AsyncMock(side_effect=RuntimeError("mất kết nối")),
        ):
            with self.assertLogs("app.api.agent", level="WARNING") as ghi:
                await api_agent._ghi_moc(PHIEN, state.suy_ra(profile=ho_so()))
        self.assertTrue(any("mốc tư vấn" in d for d in ghi.output))


class NguonSeGhiTests(unittest.IsolatedAsyncioTestCase):
    """Phép kiểm "đã có nguồn đáng tin hơn" phải so với nguồn SẮP ghi.

    Bản đầu luôn so với `chat`, nên đường xác nhận từ chối mọi lần ứng viên sửa
    một trường máy đọc từ CV. Hai đường, hai nguồn, nên phải hai kết quả.
    """

    def test_duong_de_xuat_khong_de_len_gia_tri_doc_tu_cv(self):
        hs = ho_so()
        hs["fields"]["japanese_level"] = {"value": "N4", "source": "cv"}
        nhan, loai = contract.kiem_de_xuat(
            [{"field": "japanese_level", "value": "N3"}], profile=hs
        )
        self.assertEqual(nhan, [])
        self.assertIn("đáng tin hơn", loai[0])

    def test_duong_xac_nhan_DE_DUOC_len_gia_tri_doc_tu_cv(self):
        hs = ho_so()
        hs["fields"]["japanese_level"] = {"value": "N4", "source": "cv"}
        nhan, _ = contract.kiem_de_xuat(
            [{"field": "japanese_level", "value": "N3"}],
            profile=hs,
            nguon_se_ghi="user_confirmed",
        )
        self.assertEqual(len(nhan), 1)
        self.assertEqual(nhan[0].value, "N3")

    def test_ca_hai_duong_deu_khong_de_len_gia_tri_nhan_vien_chot(self):
        hs = ho_so()
        hs["fields"]["japanese_level"] = {"value": "N4", "source": "staff"}
        for nguon in (contract.NGUON_HOI_THOAI, "user_confirmed"):
            nhan, loai = contract.kiem_de_xuat(
                [{"field": "japanese_level", "value": "N1"}],
                profile=hs,
                nguon_se_ghi=nguon,
            )
            self.assertEqual(nhan, [], f"nguồn {nguon} đè được lên giá trị của nhân viên")
            self.assertIn("đáng tin hơn", loai[0])


class SoKhachVuaNoiTests(unittest.IsolatedAsyncioTestCase):
    """Số khách vừa nhắc thì được nhắc lại. Số mô hình tự nghĩ thì không.

    Đo trên mô hình thật ngày 02/10, đúng lượt đầu tiên: khách gõ *"em làm điều
    dưỡng hai năm rồi"*, mô hình đáp *"bạn có 2 năm kinh nghiệm…"*, và chốt số
    loại cả câu vì `2` không nằm trong hồ sơ hay kết quả đối chiếu. `facts_to_save`
    mất theo — nghĩa là **việc chính của Agent gần như không bao giờ chạy được**.

    Đây là nguyên tắc khung chat đã chốt từ trước
    (`conversation/response_validator`), chỉ là đường này chưa áp.
    """

    async def _chay(self, cau_hoi: str, van_ban: str, *, khoi: str = ""):
        with patch(
            "app.advisor.client.sinh_van_ban",
            AsyncMock(return_value=(van_ban, "ok", "m")),
        ):
            return await orchestrator.tra_loi(
                cau_hoi=cau_hoi,
                profile=ho_so(),
                trang_thai=state.suy_ra(profile=ho_so()),
                khoi_doi_chieu=khoi,
            )

    async def test_so_viet_bang_chu_trong_cau_hoi_duoc_nhac_lai_bang_chu_so(self):
        ket, nguon, _ = await self._chay(
            "Em đã làm điều dưỡng hai năm rồi, vậy em hợp đơn nào?",
            '{"reply": "Bạn có 2 năm kinh nghiệm, mình ghi nhận nhé.",'
            ' "facts_to_save": [{"field": "experience_years", "value": 2,'
            ' "evidence": "em đã làm điều dưỡng hai năm rồi"}]}',
        )
        self.assertEqual(nguon, qa.NGUON_MO_HINH)
        self.assertIn("2 năm", ket.reply)
        # Và đề xuất phải sống sót — đây mới là thứ cả tính năng tồn tại để làm.
        self.assertEqual(len(ket.de_xuat), 1)
        self.assertEqual(ket.de_xuat[0].field, "experience_years")

    async def test_so_khach_go_bang_chu_so_cung_duoc_nhac_lai(self):
        ket, nguon, _ = await self._chay(
            "Em chuẩn bị được 90 triệu, có đủ không?",
            '{"reply": "Bạn chuẩn bị được 90 triệu, mình ghi nhận nhé."}',
        )
        self.assertEqual(nguon, qa.NGUON_MO_HINH)

    async def test_so_mo_hinh_TU_NGHI_RA_van_bi_chan(self):
        """Lá chắn không được nới: số không có trong câu khách lẫn khối dữ liệu."""
        ket, nguon, _ = await self._chay(
            "Em làm hai năm rồi, chi phí bao nhiêu?",
            '{"reply": "Tổng chi phí của bạn là 250 triệu đồng.",'
            ' "facts_to_save": [{"field": "experience_years", "value": 2}]}',
        )
        self.assertEqual(nguon, qa.NGUON_KHONG_BIET)
        self.assertEqual(ket.reply, qa.CAU_KHONG_BIET)
        # Câu bị loại thì đề xuất bỏ theo, kể cả đề xuất đó vốn hợp lệ.
        self.assertEqual(ket.de_xuat, ())

    async def test_cau_hoi_khong_mo_duong_cho_so_trong_bo_nho(self):
        """Mở theo câu hỏi, không mở theo bộ nhớ chung."""
        with patch(
            "app.advisor.client.sinh_van_ban",
            AsyncMock(return_value=('{"reply": "Chi phí là 123 triệu."}', "ok", "m")),
        ):
            _ket, nguon, _ = await orchestrator.tra_loi(
                cau_hoi="Chi phí thế nào?",
                profile=ho_so(),
                trang_thai=state.suy_ra(profile=ho_so()),
                khoi_doi_chieu="",
                bo_nho={
                    "moi_quan_tam": [
                        {"chu_de": "chi_phi", "so_lan": 2, "cau_gan_nhat": "123 triệu à?"}
                    ]
                },
            )
        self.assertEqual(nguon, qa.NGUON_KHONG_BIET)

    def test_doi_so_bang_chu_khong_cham_cau_tra_loi(self):
        """Chỉ mở rộng tập cho phép, không áp lên câu trả lời.

        Áp lên câu trả lời là mở một hướng khác hẳn: nó biến "một số đơn" thành
        con số 1 rồi đem đi so, và chặn oan những câu hoàn toàn đúng.
        """
        ra = orchestrator._so_khach_vua_noi("Em làm hai năm, có một số đơn nào hợp?")
        self.assertIn("2", ra)
        self.assertIn("hai năm", ra, "phải giữ cả câu gốc")

    def test_khong_co_cau_hoi_thi_khong_mo_gi(self):
        self.assertEqual(orchestrator._so_khach_vua_noi(""), "")


class LyDoThatBaiPhaiDocDuocTests(unittest.IsolatedAsyncioTestCase):
    """Một dòng log không nói gì thì bằng không có log.

    `str()` của `httpx.ReadTimeout` là chuỗi rỗng, nên dòng cũ in ra đúng
    `"không gọi được gemini-3.8-flash: "`. Timeout là lỗi truyền hay gặp nhất,
    nên chỗ im lặng nhất của log lại rơi đúng vào chỗ cần đọc nhất.

    Gặp thật ngày 02/10 khi đo Agent: hai lượt liền trả lý do rỗng, không có cách
    nào biết đó là hết hạn mức, mất mạng, hay quá thời gian chờ.
    """

    async def test_timeout_khong_loi_van_ghi_duoc_ten_loai(self):
        import httpx

        from app.advisor import client as advisor_client

        with patch.object(
            advisor_client.settings, "advisor_api_key", "khoa-thu"
        ), patch("httpx.AsyncClient.post", AsyncMock(side_effect=httpx.ReadTimeout(""))):
            with self.assertLogs("app.advisor.client", level="WARNING") as ghi:
                cau, ly_do = await advisor_client._goi_mot_lan(
                    "model-thu", "prompt", temperature=0.3, max_tokens=100
                )
        self.assertIsNone(cau)
        self.assertEqual(ly_do, advisor_client.LY_DO_KHONG_GOI_DUOC)
        dong = "\n".join(ghi.output)
        self.assertIn("ReadTimeout", dong, f"log không nói được lỗi gì: {dong!r}")
        # Và không được kết thúc bằng dấu hai chấm trống.
        self.assertFalse(
            dong.rstrip().endswith(":"), f"log kết thúc bằng hai chấm trống: {dong!r}"
        )

    async def test_loi_co_loi_thi_ghi_ca_loai_va_loi(self):
        import httpx

        from app.advisor import client as advisor_client

        with patch.object(
            advisor_client.settings, "advisor_api_key", "khoa-thu"
        ), patch(
            "httpx.AsyncClient.post",
            AsyncMock(side_effect=httpx.ConnectError("mạng hỏng")),
        ):
            with self.assertLogs("app.advisor.client", level="WARNING") as ghi:
                await advisor_client._goi_mot_lan(
                    "model-thu", "prompt", temperature=0.3, max_tokens=100
                )
        dong = "\n".join(ghi.output)
        self.assertIn("ConnectError", dong)
        self.assertIn("mạng hỏng", dong)


class NguongChoRiengTests(unittest.IsolatedAsyncioTestCase):
    """Agent xin khối JSON nên sinh lâu hơn; ngưỡng chờ phải rộng hơn.

    Đo thật ngày 02/10: hai lượt liền trả `ReadTimeout` trong khi vẫn còn hạn
    mức. Ngưỡng chung 12 giây là đúng cho phòng tư vấn theo đơn — nó trả về một
    câu thuần — nhưng chật cho một khối có `reply` cùng bốn trường nữa.
    """

    async def test_agent_truyen_nguong_cho_rieng_xuong_tang_truyen(self):
        goi = AsyncMock(return_value=("{}", "ok", "m"))
        with patch("app.advisor.client.sinh_van_ban", goi):
            await orchestrator.tra_loi(
                cau_hoi="x?",
                profile=ho_so(),
                trang_thai=state.suy_ra(profile=ho_so()),
                khoi_doi_chieu="",
            )
        self.assertEqual(
            goi.await_args.kwargs.get("timeout"), orchestrator.NGUONG_CHO_GIAY
        )

    async def test_nguong_rieng_rong_hon_nguong_chung(self):
        from app.core.config import settings

        self.assertGreater(orchestrator.NGUONG_CHO_GIAY, settings.advisor_timeout_seconds)

    async def test_nguong_khong_vo_han(self):
        """Ứng viên đang ngồi chờ. Sau nửa phút thì câu trả lời đến cũng đã muộn."""
        self.assertLessEqual(orchestrator.NGUONG_CHO_GIAY, 30.0)

    async def test_duong_tu_van_theo_don_khong_bi_noi_nguong(self):
        """Nới ngưỡng chung là bắt ứng viên ở đường kia chờ lâu hơn mà không được gì."""
        import inspect

        from app.advisor import qa as advisor_qa

        nguon = inspect.getsource(advisor_qa.tra_loi)
        self.assertNotIn("timeout=", nguon)


class XacNhanMotTruongKhongXoaPhanKhacTests(unittest.IsolatedAsyncioTestCase):
    """Xác nhận một trường không được xoá phần còn lại của hồ sơ.

    Gặp thật trên luồng gửi CV ngày 05/10. Chuỗi sự việc:

    1. `api/agent._ghi_mot_truong` chỉ dựng phần đang sửa, rồi truyền `None` cho
       phần kia.
    2. `apply_changes` ghi thẳng `None` vào database → nguyện vọng mất sạch.
    3. Vài cú bấm sau, bước xác nhận hồ sơ đọc `profile.get("preferences", {})`.
       `.get` chỉ trả mặc định khi **thiếu khóa**; khóa có mặt với giá trị `None`
       thì nó trả `None`, và `None.items()` ném `AttributeError`.
    4. Máy chủ trả 500, giao diện hiện **"Không kết nối được máy chủ"**.

    Ba tầng, ba ca. Tầng nào cũng đủ để chặn một mình, và đó là chủ ý: hỏng ở
    tầng một thì nổ ở tầng ba, cách nhau vài cú bấm và một câu báo lỗi sai hướng.
    """

    async def test_tang_1_ghi_mot_truong_luon_dung_ca_hai_phan(self):
        from app.api import agent as api_agent

        hs = ho_so()
        hs["preferences"] = {
            "desired_prefecture": {"value": "Tokyo", "source": "user_confirmed"}
        }
        da_ghi: dict = {}

        async def _ap(session_id, **kw):
            da_ghi.update(kw)
            return {**hs, "version": 2}

        with patch.object(profiles, "apply_changes", _ap):
            await api_agent._ghi_mot_truong(
                PHIEN, hs, {"fields": {"birth_year": 1999}}
            )

        self.assertIsNotNone(da_ghi["preferences"], "nguyện vọng bị truyền None")
        self.assertIn("desired_prefecture", da_ghi["preferences"])
        self.assertIn("birth_year", da_ghi["fields"])

    async def test_tang_2_cua_ghi_coi_None_la_giu_nguyen(self):
        """Bất biến 'hồ sơ luôn có cả hai phần' canh ở cửa ghi, không bắt từng người gọi nhớ."""
        ghi = AsyncMock(return_value={"version": 2})
        with patch("app.db.candidate_profiles.get_db") as lay_db:
            lay_db.return_value = {profiles.COLLECTION: type(
                "C", (), {"find_one_and_update": ghi}
            )()}
            await profiles.apply_changes(
                PHIEN,
                expected_version=1,
                fields={"birth_year": {"value": 1999}},
                preferences=None,
                history={},
            )
        dat = ghi.await_args.args[1]["$set"]
        self.assertIn("fields", dat)
        self.assertNotIn(
            "preferences",
            dat,
            "truyền None mà vẫn ghi `preferences` — nguyện vọng của ứng viên bị xoá",
        )

    def test_tang_3_xac_nhan_ho_so_chiu_duoc_preferences_None(self):
        """Hồ sơ đã hỏng vẫn còn trong database; chủ của chúng đáng được đi tiếp."""
        import ast
        import pathlib

        nguon = (
            pathlib.Path(__file__).resolve().parent.parent / "app" / "api" / "profiles.py"
        ).read_text(encoding="utf-8")
        cay = ast.parse(nguon)
        ham = next(
            n
            for n in ast.walk(cay)
            if isinstance(n, ast.AsyncFunctionDef) and n.name == "_apply"
        )
        # `profile.get("x", {})` nổ khi khóa có mặt với giá trị None. Phải dùng
        # `profile.get("x") or {}`.
        for node in ast.walk(ham):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Attribute) or node.func.attr != "get":
                continue
            if len(node.args) == 2 and isinstance(node.args[0], ast.Constant):
                self.assertNotIn(
                    node.args[0].value,
                    ("fields", "preferences"),
                    f"`.get({node.args[0].value!r}, ...)` nổ khi khóa có mặt với giá trị None",
                )


class DiemPhuHopChuaCoNghiaThiKhongHienTests(unittest.TestCase):
    """Không hiện "5/100" cạnh "đạt các điều kiện bắt buộc".

    Điểm mềm chấm theo **nguyện vọng** ứng viên nêu: khu vực, loại hình cơ sở,
    lương, chi phí. Chưa nêu nguyện vọng nào thì cả bốn dòng đều chưa rõ và tổng
    điểm xuống gần 0.

    Khi ấy màn hình hiện "5/100 điểm phù hợp" ngay cạnh dòng "đạt các điều kiện
    bắt buộc". Hai câu đó cạnh nhau nói một điều sai: hồ sơ đạt đủ bảy điều kiện
    cứng, còn 5/100 đọc như "chỉ hợp 5 phần trăm" — và người đọc bỏ đơn mà họ
    thật sự nộp được.

    Con số không sai về tính toán, nó sai về **ý nghĩa**: nó đo mức khớp với
    nguyện vọng, mà nguyện vọng chưa có.

    Thấy trên trình duyệt thật ngày 01/10 và vẫn còn ngày 05/10.
    """

    @staticmethod
    def _soft(outcome: str, points: int = 0):
        from app.matching.engine import SoftRow

        return SoftRow(
            key="k",
            label="Khu vực",
            requirement_text="r",
            candidate_text="c",
            outcome=outcome,
            points=points,
            max_points=40,
        )

    def test_chua_neu_nguyen_vong_nao_thi_khong_xep_hang_duoc(self):
        from app.matching.engine import xep_hang_duoc

        self.assertFalse(xep_hang_duoc(tuple(self._soft("unknown") for _ in range(4))))

    def test_mot_nguyen_vong_la_du_de_xep_hang(self):
        """Khách chỉ nêu Tokyo thì thứ tự giữa các đơn ĐÃ có nghĩa.

        Đòi đủ bốn dòng mới cho xếp hạng là giấu mất một thứ tự đúng.
        """
        from app.matching.engine import xep_hang_duoc

        self.assertTrue(
            xep_hang_duoc(
                (
                    self._soft("same_prefecture", 40),
                    self._soft("unknown"),
                    self._soft("unknown"),
                    self._soft("unknown"),
                )
            )
        )

    def test_don_bi_loai_khong_co_dong_mem_nao(self):
        """Đơn bị loại không được chấm điểm, nên cũng không xếp hạng được."""
        from app.matching.engine import xep_hang_duoc

        self.assertFalse(xep_hang_duoc(()))

    def test_payload_cho_danh_sach_don_mang_co_score_ranked(self):
        from app.services import matching_service

        item = {
            "code": "DH-0001",
            "title": "x",
            "employer_name": "y",
            "prefecture": "Tokyo",
            "employer_type": "vien_duong_lao",
            "program": "tokutei_ginou",
            "deadline": "2026-12-15",
            "eligible": True,
            "score": 5,
            "rank": 1,
            "hard_rows": [],
            "soft_rows": [self._soft("unknown").as_dict() for _ in range(4)],
            "gaps": [],
            "missing_info": [],
            "labels": {},
        }
        ra = matching_service.public_item(item)
        self.assertIn("score_ranked", ra)
        self.assertFalse(ra["score_ranked"])

    def test_payload_cua_phong_tu_van_theo_don_cung_mang_co(self):
        """Hai màn hình cùng hỏi câu này; mỗi nơi tự suy thì sớm muộn lệch nhau."""
        from app.consultation import advice as advice_builder

        self.assertIn("score_ranked", advice_builder.Advice.__dataclass_fields__)

    def test_hai_man_hinh_khong_tu_suy_tu_score(self):
        """Giao diện phải đọc cờ của máy chủ, không tự đoán từ con số điểm."""
        import pathlib
        import re

        goc = pathlib.Path(__file__).resolve().parents[2] / "frontend"
        for ten in ("MatchCard.tsx", "OrderAdvicePanel.tsx"):
            nguon = (goc / "components" / "candidate" / ten).read_text(encoding="utf-8")
            self.assertIn("score_ranked", nguon, f"{ten} không đọc cờ của máy chủ")
            # Tự suy kiểu `score < 10` là dựng ngưỡng thứ hai ở nơi không biết
            # vì sao điểm thấp.
            self.assertIsNone(
                re.search(r"score\s*[<>]=?\s*\d", nguon),
                f"{ten} tự dựng ngưỡng trên `score` thay vì đọc cờ",
            )
            # **Hai nhánh phải loại trừ nhau.**
            #
            # Phá thử 05/10: bỏ điều kiện ở khối hiện con số thì phép tìm chuỗi
            # trên vẫn xanh, vì khối thông báo "chưa xếp hạng được" cũng chứa
            # `score_ranked`. Hậu quả thật là màn hình hiện **cả hai cùng lúc**:
            # một con số điểm, và ngay dưới là câu nói chưa xếp hạng được.
            #
            # Nên phải có đủ cả hai nhánh: một cho trường hợp xếp hạng được, một
            # cho trường hợp chưa.
            self.assertIn(
                "score_ranked === false",
                nguon,
                f"{ten} thiếu nhánh cho trường hợp CHƯA xếp hạng được",
            )
            self.assertTrue(
                "score_ranked !== false" in nguon or "score_ranked === false ? (" in nguon,
                f"{ten}: khối hiện con số không được canh bởi cờ — hai nhánh sẽ hiện cùng lúc",
            )


class ChuaXepHangThiKhongNoiXepHangTests(unittest.TestCase):
    """Quy tắc "chưa xếp hạng được" phải áp **xuyên suốt**, không chỉ ô điểm.

    Bản sửa 05/10 chỉ ẩn ô điểm trên màn hình. Nhưng câu giải thích nằm **ngay
    bên dưới ô đó** và vẫn nói ra đúng con số vừa ẩn:

        "Xếp hạng 1 với 5/100 điểm."

    Bốn chỗ cùng nói về thứ hạng, và cả bốn phải tuân cùng một quy tắc:

    1. Ô điểm trên thẻ đơn — đã sửa 05/10.
    2. Nhãn "Phù hợp nhất #1".
    3. Câu giải thích sinh bằng mã (`explain.render_template_text`).
    4. **Khối ngữ cảnh mô hình đọc** (`explain.render_block`) — chỗ này nặng
       nhất: nó vừa mời mô hình nhắc lại một thứ hạng chưa có nghĩa, vừa biến
       con số ấy thành số hợp lệ để chốt số cho qua ở bất cứ đâu trong câu.
    5. **Lý do "nhờ ..." trong lượt mở đầu** (`mo_dau._diem_manh`) — thêm ngày
       05/10 sau khi bộ nghiệm thu xuyên suốt bắt được, xem ca dưới cùng.
    """

    @staticmethod
    def _item(*, co_nguyen_vong: bool):
        from app.matching.engine import CriterionRow, MatchItem, SoftRow

        def soft(outcome, pts):
            return SoftRow(
                key="region",
                label="Khu vực",
                requirement_text="khu vực Tokyo",
                candidate_text="mong muốn Tokyo" if pts else "chưa nêu nguyện vọng",
                outcome=outcome,
                points=pts,
                max_points=40,
            )

        soft_rows = (
            (soft("same_prefecture", 40), soft("unknown", 0))
            if co_nguyen_vong
            else (soft("unknown", 0), soft("unknown", 0))
        )
        return MatchItem(
            code="DH-0001",
            title="Điều dưỡng viện dưỡng lão Tokyo",
            employer_name="Viện dưỡng lão Sakura",
            prefecture="Tokyo",
            region_group="kanto",
            employer_type="vien_duong_lao",
            program="tokutei_ginou",
            deadline="2026-12-15",
            eligible=True,
            score=sum(r.points for r in soft_rows),
            rank=1,
            hard_rows=(
                CriterionRow(
                    key="japanese",
                    label="Tiếng Nhật",
                    requirement_text="yêu cầu N4",
                    candidate_text="ứng viên N4",
                    result="DAT",
                ),
            ),
            soft_rows=soft_rows,
            gaps=(),
            missing_info=(),
            labels={},
        )

    def test_cau_giai_thich_khong_noi_xep_hang_khi_chua_co_nguyen_vong(self):
        from app.matching import explain

        cau = explain.render_template_text(self._item(co_nguyen_vong=False))
        self.assertNotIn("Xếp hạng", cau)
        self.assertNotIn("/100", cau)
        self.assertIn("Chưa xếp hạng được", cau)

    def test_cau_giai_thich_VAN_noi_xep_hang_khi_da_co_nguyen_vong(self):
        """Không được tắt luôn: có nguyện vọng thì thứ hạng là thông tin thật."""
        from app.matching import explain

        cau = explain.render_template_text(self._item(co_nguyen_vong=True))
        self.assertIn("Xếp hạng 1", cau)
        self.assertIn("40/100", cau)

    def test_khoi_cho_mo_hinh_doc_khong_mang_diem_khi_chua_xep_hang_duoc(self):
        """Khối này vừa là ngữ cảnh mô hình đọc, vừa là tập số chốt số so vào."""
        from app.matching import explain

        khoi = explain.render_block(self._item(co_nguyen_vong=False))
        self.assertIn("chưa xếp hạng được", khoi)
        # Không khẳng định một thứ hạng, và không mang điểm.
        #
        # Đừng tìm riêng chữ "hạng": nó nằm trong chính câu thay thế "chưa xếp
        # HẠNG được". Thứ phải vắng là **lời khẳng định** `hạng <số>` và cụm
        # `tổng .../100`.
        import re as _re

        self.assertIsNone(_re.search(r"hạng\s*\d", khoi))
        self.assertNotIn("tổng ", khoi)
        self.assertNotIn("/100", khoi)

        # Và con số 5 không được nằm trong tập số cho phép.
        from app.advisor import phrasing

        self.assertNotIn("5", phrasing.so_trong(khoi))

    def test_khoi_cho_mo_hinh_VAN_mang_diem_khi_da_co_nguyen_vong(self):
        from app.matching import explain

        khoi = explain.render_block(self._item(co_nguyen_vong=True))
        self.assertIn("tổng 40/100", khoi)
        self.assertIn("hạng 1", khoi)

    def test_luot_mo_dau_khong_noi_xep_hang_cao_nhat_khi_chua_so_duoc(self):
        """"Đang xếp hạng cao nhất" với mọi đơn 0 điểm là biến thứ tự ngẫu nhiên
        thành một lời khuyên."""
        log = {
            "total_considered": 18,
            "eligible_count": 2,
            "items": [
                {
                    "code": "DH-0016",
                    "title": "Hộ lý viện dưỡng lão Sendai",
                    "eligible": True,
                    "rank": 1,
                    "soft_rows": [],
                },
            ],
        }
        cau = mo_dau.sau_matching(log)
        self.assertNotIn("cao nhất", cau)
        self.assertNotIn("phù hợp nhất", cau)
        self.assertIn("chưa so được thứ tự", cau.lower())

    def test_nhan_thu_hang_tren_the_cung_theo_co(self):
        import pathlib

        nguon = (
            pathlib.Path(__file__).resolve().parents[2]
            / "frontend" / "components" / "candidate" / "MatchCard.tsx"
        ).read_text(encoding="utf-8")
        # Tìm theo mẫu chỉ có trong JSX, không tìm chuỗi nhãn trơ.
        #
        # `find("Phù hợp nhất #")` khớp vào khối BÌNH LUẬN phía trên trước
        # — chính dòng bình luận giải thích vì sao nhãn phải theo cờ. Ca
        # kiểm thử khi ấy đỏ vì một lý do không liên quan gì tới mã sản phẩm.
        i = nguon.find("#{item.rank}")
        self.assertGreater(i, 0, "không thấy nhãn thứ hạng trong JSX")
        # Điều kiện canh nhãn phải nhắc tới cờ, không chỉ `rank !== null`.
        #
        # Lấy đúng dòng điều kiện ngay trước nhãn, không lấy một cửa sổ ký tự:
        # cửa sổ 200 ký tự chỉ bắt được khối bình luận phía trên và ca kiểm thử
        # đỏ vì một lý do không liên quan.
        dong = nguon[:i].rstrip().splitlines()
        dieu_kien = next(
            (d for d in reversed(dong) if "item.rank" in d),
            "",
        )
        self.assertIn(
            "score_ranked",
            dieu_kien,
            f"nhãn thứ hạng không theo cờ của máy chủ; điều kiện là: {dieu_kien.strip()!r}",
        )

    def test_khong_khen_dong_chua_ro_thanh_diem_manh(self):
        """"Nhờ chi phí" khi chính dòng ấy ghi "chưa rõ khả năng".

        `weights.json` cho dòng chi phí **5 điểm khi chưa rõ** — có chủ ý, để đơn
        không công bố chi phí khỏi bị xếp dưới đơn đã biết là quá khả năng. Hệ quả
        ngoài ý muốn: khách chưa nêu ngân sách thì MỌI đơn có 5 điểm chi phí.

        `mo_dau._diem_manh` lọc theo `points > 0` nên nhặt đúng dòng đó và câu mở
        đầu thành *"phù hợp nhất, nhờ chi phí"* — khen một thứ chưa ai biết. Trong
        khi `explain.render_template_text` ngay bên cạnh đã lọc thêm `outcome`.

        Hai chỗ trả lời cùng một câu hỏi thì phải cùng một luật. Ca này chốt điều
        đó, và kiểm cả chiều ngược lại để không lọc oan dòng có thật.
        """
        def log_voi(outcome, points, label):
            return {
                "total_considered": 18,
                "eligible_count": 1,
                "items": [
                    {
                        "code": "DH-0016",
                        "title": "Hộ lý viện dưỡng lão Sendai",
                        "eligible": True,
                        "rank": 1,
                        "soft_rows": [
                            {
                                "key": "cost",
                                "label": label,
                                "outcome": outcome,
                                "points": points,
                            }
                        ],
                    }
                ],
            }

        cau = mo_dau.sau_matching(log_voi("unknown", 5, "Chi phí"))
        self.assertNotIn("nhờ chi phí", cau.lower())
        self.assertNotIn("phù hợp nhất", cau)
        self.assertIn("chưa so được thứ tự", cau.lower())

        # Chiều ngược: chi phí trong khả năng thật thì VẪN phải được nêu, nếu
        # không thì bản sửa chỉ là bịt miệng cả hai trường hợp.
        cau_that = mo_dau.sau_matching(log_voi("within", 10, "Chi phí"))
        self.assertIn("nhờ chi phí", cau_that.lower())
        self.assertIn("phù hợp nhất", cau_that)



class BanGiaoGomMoiPhamViTests(unittest.IsolatedAsyncioTestCase):
    """Bản bàn giao phải gom **mọi** lượt, cả hội thoại về từng đơn.

    `list_turns(session_id, None)` chỉ lấy phạm vi hồ sơ — đúng cho giao diện,
    sai cho bàn giao. Khách hỏi năm câu trong phòng tư vấn đơn DH-0001 rồi bấm
    "xin gặp nhân viên" thì nhân viên nhận một phiếu **không có câu nào khách đã
    hỏi**, và gọi điện với bối cảnh trống.
    """

    def test_ban_giao_in_duoc_cau_hoi_ve_tung_don(self):
        tt = state.suy_ra(profile=ho_so(), log=nhat_ky())
        ban = ban_giao.dung(
            profile=ho_so(),
            trang_thai=tt,
            log=nhat_ky(),
            luot_hoi=[
                {"question": "Em còn thiếu gì?", "source": "mo_hinh"},
                {
                    "question": "Đơn này lương bao nhiêu?",
                    "source": "khong_biet",
                    "job_order_code": "DH-0001",
                },
            ],
        )
        self.assertIn("Em còn thiếu gì?", ban)
        self.assertIn("Đơn này lương bao nhiêu?", ban)
        self.assertIn("(về đơn DH-0001)", ban)

    def test_hai_duong_ban_giao_dung_cung_mot_tap_du_lieu(self):
        """Đường cho khách xem trước và đường đính vào yêu cầu phải khớp nhau.

        Lệch một dòng là lời hứa "xem trước thứ nhân viên sẽ đọc" thành sai.
        """
        import pathlib
        import re

        goc = pathlib.Path(__file__).resolve().parent.parent / "app" / "api"
        for ten in ("agent.py", "support.py"):
            nguon = (goc / ten).read_text(encoding="utf-8")
            khoi = re.findall(r"luot_hoi=await advisor_turns\.(\w+)\(", nguon)
            self.assertTrue(khoi, f"{ten}: không thấy chỗ nạp lượt cho bản bàn giao")
            for ham in khoi:
                self.assertEqual(
                    ham,
                    "list_all_turns",
                    f"{ten}: bản bàn giao nạp bằng {ham} — thiếu hội thoại theo đơn",
                )


class ListAllTurnsLayMoiPhamViTests(unittest.IsolatedAsyncioTestCase):
    """`list_all_turns` phải không lọc theo đơn nào cả.

    Phá thử 05/10: thêm `"job_order_code": None` vào bộ lọc của chính hàm này
    thì **không ca nào đỏ** — vì các ca khác chỉ kiểm *nơi gọi* có dùng đúng tên
    hàm, và kiểm `ban_giao` in được câu hỏi theo đơn khi **được truyền sẵn** dữ
    liệu. Không ca nào chạm vào câu truy vấn.

    Hậu quả nếu lọt: tên hàm nói "all" nhưng nó lấy đúng một phạm vi, và bản bàn
    giao lại thiếu hội thoại theo đơn — đúng lỗi vừa sửa, quay lại nguyên vẹn
    dưới một cái tên trông đã đúng.
    """

    async def test_truy_van_chi_loc_theo_phien(self):
        ghi_lai: dict = {}

        class _Cursor:
            def sort(self, *a, **k):
                return self

            def limit(self, *a, **k):
                return self

            def __aiter__(self):
                async def _g():
                    if False:
                        yield {}

                return _g()

        class _Col:
            def find(self, query, projection=None):
                ghi_lai["query"] = query
                return _Cursor()

        with patch("app.db.advisor_turns.get_db", lambda: {advisor_turns.COLLECTION: _Col()}):
            await advisor_turns.list_all_turns(PHIEN)

        self.assertEqual(ghi_lai["query"], {"session_id": PHIEN})
        self.assertNotIn(
            "job_order_code",
            ghi_lai["query"],
            "list_all_turns lọc theo đơn — bản bàn giao sẽ thiếu hội thoại theo đơn",
        )

    async def test_list_turns_thi_VAN_loc_theo_don(self):
        """Hàm cũ phải giữ nguyên hành vi: giao diện cần đúng một phạm vi."""
        ghi_lai: dict = {}

        class _Cursor:
            def sort(self, *a, **k):
                return self

            def limit(self, *a, **k):
                return self

            def __aiter__(self):
                async def _g():
                    if False:
                        yield {}

                return _g()

        class _Col:
            def find(self, query, projection=None):
                ghi_lai["query"] = query
                return _Cursor()

        with patch("app.db.advisor_turns.get_db", lambda: {advisor_turns.COLLECTION: _Col()}):
            await advisor_turns.list_turns(PHIEN, None)

        self.assertEqual(
            ghi_lai["query"], {"session_id": PHIEN, "job_order_code": None}
        )
