# -*- coding: utf-8 -*-
"""Chạy năm ca qua **HTTP thật**, trên backend đang chạy.

    venv/Scripts/python.exe -m scripts.e2e_xuyen_suot [--url http://127.0.0.1:8020]

## Khác gì `nghiem_thu_xuyen_suot`

Bộ kia gọi hàm trong cùng tiến trình: nhanh, tất định, chạy được khi hết hạn mức
— nhưng nó **không đi qua** cookie đã ký, bộ giới hạn theo IP, tầng lưu MongoDB,
hay lớp chuyển JSON. Ba lỗi nặng nhất của tuần này nằm đúng ở những chỗ ấy:

- `preferences=None` xoá trắng hồ sơ → 500, màn hình hiện "Không kết nối được
  máy chủ". Mọi test trong tiến trình đều xanh.
- Bản bàn giao dựng **trước khi** lịch hẹn tồn tại, nên mục khung giờ rỗng.
- `.next` hỏng khi build lúc dev server còn chạy.

Nên bộ này không đo logic. Nó đo **cái chạy thật**.

## Không gọi mô hình trừ khi được yêu cầu

Mặc định bỏ qua lượt hỏi trợ lý, vì mỗi lượt tốn một phần hạn mức 20 lượt/ngày.
Thêm `--hoi` để chạy đúng một lượt thật trên một ca.
"""
import argparse
import json
import urllib.error
import urllib.request
from datetime import date

import app  # noqa: F401 — đặt stdout về UTF-8
from scripts import so_phien_e2e


class Khach:
    """Một người dùng: giữ cookie phiên y như trình duyệt."""

    def __init__(self, goc: str) -> None:
        self.goc = goc.rstrip("/")
        self.cookie = ""

    def goi(self, duong: str, *, method="GET", than=None):
        req = urllib.request.Request(
            f"{self.goc}{duong}",
            method=method,
            data=None if than is None else json.dumps(than).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        if self.cookie:
            req.add_header("Cookie", self.cookie)
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                dat = r.read().decode("utf-8")
                # Giữ cookie phiên: mã phiên nằm trong cookie đã ký, không nằm
                # trong thân yêu cầu — bỏ nó là mọi lời gọi sau trả 401/403.
                for h in r.headers.get_all("Set-Cookie") or ():
                    self.cookie = h.split(";", 1)[0]
                return r.status, (json.loads(dat) if dat else None)
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode("utf-8") or "{}")


HOM_NAY = date.today()

CA = [
    ("N4-PHU-HOP", {
        "full_name": "Ca Một", "japanese_level": "N4", "education_level": "cao_dang",
        "birth_year": HOM_NAY.year - 27, "gender": "nu", "experience_years": 3,
        "care_experience": True,
    }, {
        "desired_prefecture": "Tokyo", "desired_region_group": "kanto",
        "desired_employer_type": "vien_duong_lao", "salary_expectation_jpy": 190000,
        "budget_vnd": 90000000,
    }),
    ("CHUA-HOC-TIENG", {
        "full_name": "Ca Hai", "japanese_level": "chua_hoc",
        "education_level": "trung_cap", "birth_year": HOM_NAY.year - 19,
        "gender": "nu", "care_experience": False,
    }, {"desired_employer_type": "vien_duong_lao"}),
    ("THIEU-THONG-TIN", {"full_name": "Ca Ba", "japanese_level": "N4"}, {}),
    ("QUA-TUOI", {
        "full_name": "Ca Bốn", "japanese_level": "N4", "education_level": "cao_dang",
        "birth_year": HOM_NAY.year - 38, "gender": "nam",
    }, {"desired_prefecture": "Tokyo"}),
    ("DOI-DON", {
        "full_name": "Ca Năm", "japanese_level": "N4", "education_level": "cao_dang",
        "birth_year": HOM_NAY.year - 25, "gender": "nu", "experience_years": 2,
        "care_experience": True,
    }, {"desired_prefecture": "Tokyo", "desired_region_group": "kanto"}),
]


# --- Kỳ vọng riêng từng ca ---------------------------------------------------
#
# Bản đầu của bộ này chỉ kiểm những thứ **đúng với mọi hồ sơ**: có trả 200
# không, có dựng được lượt mở đầu không, câu giải thích có nói điểm khi chưa
# xếp hạng được không. Chủ đồ án tái hiện được chỗ hở: giả lập máy chủ trả
# **cùng một đơn đạt cho mọi hồ sơ**, kể cả khách chưa học tiếng, thì cả năm ca
# vẫn báo đạt.
#
# Đó là một bộ đo nói "đạt" về một hệ thống sai hoàn toàn. Nên mỗi ca cần kỳ
# vọng của riêng nó.
#
# Nguyên tắc chọn kỳ vọng: **không ghi cứng con số lấy từ dữ liệu**. Danh mục
# đơn thay đổi theo thời gian, nên "phải có đúng 11 đơn đạt" sẽ đỏ vì một lý do
# không liên quan tới mã nguồn. Thay vào đó kiểm những **quan hệ** không được
# phép đổi dù danh mục đổi thế nào.


def _ma_dat(muc):
    return {m["code"] for m in muc}


def ky_vong_rieng(ket: dict) -> list[str]:
    """Kiểm kỳ vọng từng ca, trên kết quả HTTP của cả năm ca.

    Nhận `{mã ca: {...}}`, trả danh sách chỗ hỏng.
    """
    hong = []
    co = lambda m: ket.get(m) or {}

    # 1. Chưa học tiếng thì KHÔNG đơn nào nộp được.
    #
    # Ca mạnh nhất của cả bộ, và là ca chủ đồ án dùng để bắt lỗi. `chua_hoc` nằm
    # dưới N5, mà mọi đơn đang mở đều đòi từ N5 lên. Một máy chủ trả đơn đạt cho
    # hồ sơ này là đang bỏ qua bộ lọc cứng quan trọng nhất.
    n = co("CHUA-HOC-TIENG").get("so_dat")
    if n != 0:
        hong.append(
            f"CHUA-HOC-TIENG: có {n} đơn đạt, phải là 0 — "
            "chưa học tiếng nằm dưới N5 nên không đơn nào nhận"
        )

    # 2. Tập đơn đạt phải KHÁC NHAU giữa các ca.
    #
    # Chốt chặn trực tiếp cho "trả cùng một đơn cho mọi hồ sơ". Hai hồ sơ khác
    # nhau về tuổi và nguyện vọng mà ra cùng một tập đơn thì hoặc bộ đối chiếu
    # không đọc hồ sơ, hoặc nó đọc rồi bỏ qua.
    tap = {m: _ma_dat(co(m).get("muc") or []) for m in ("N4-PHU-HOP", "QUA-TUOI")}
    if tap["N4-PHU-HOP"] and tap["N4-PHU-HOP"] == tap["QUA-TUOI"]:
        hong.append(
            "N4-PHU-HOP và QUA-TUOI ra cùng một tập đơn — "
            "bộ đối chiếu không phân biệt được 27 tuổi với 38 tuổi"
        )

    # 3. Quá tuổi thì phải ít đơn hơn hẳn.
    a = co("N4-PHU-HOP").get("so_dat")
    b = co("QUA-TUOI").get("so_dat")
    if isinstance(a, int) and isinstance(b, int) and b >= a:
        hong.append(f"QUA-TUOI có {b} đơn, không ít hơn N4-PHU-HOP ({a}) dù 38 tuổi")

    # 4. Nêu nguyện vọng rõ thì đơn hạng nhất phải TRÙNG nguyện vọng ấy.
    #
    # Hồ sơ này muốn Tokyo và viện dưỡng lão. Đơn đứng đầu mà ở tỉnh khác hoặc
    # loại cơ sở khác thì điểm mềm không có tác dụng gì — và điểm mềm chính là
    # thứ duy nhất quyết định thứ tự.
    nhat = next((m for m in co("N4-PHU-HOP").get("muc") or [] if m.get("rank") == 1), None)
    if nhat is None:
        hong.append("N4-PHU-HOP: không có đơn nào hạng 1")
    else:
        if nhat.get("prefecture") != "Tokyo":
            hong.append(
                f"N4-PHU-HOP: đơn hạng 1 ở {nhat.get('prefecture')!r} "
                "dù khách nêu nguyện vọng Tokyo"
            )
        if nhat.get("employer_type") != "vien_duong_lao":
            hong.append(
                f"N4-PHU-HOP: đơn hạng 1 là {nhat.get('employer_type')!r} "
                "dù khách nêu nguyện vọng viện dưỡng lão"
            )
        if not nhat.get("score_ranked"):
            hong.append("N4-PHU-HOP: nêu đủ nguyện vọng mà vẫn báo chưa xếp hạng được")

    # 5. Chưa nêu nguyện vọng nào thì KHÔNG đơn nào được báo xếp hạng được.
    for m in co("THIEU-THONG-TIN").get("muc") or []:
        if m.get("score_ranked"):
            hong.append(
                f"THIEU-THONG-TIN: {m['code']} báo xếp hạng được "
                "dù khách chưa nêu nguyện vọng nào"
            )
            break

    # 6. Hồ sơ khuyết thì phải sinh câu hỏi; hồ sơ đủ thì không.
    #
    # Hai chiều, vì chỉ kiểm một chiều thì một máy chủ luôn trả danh sách rỗng
    # — hoặc luôn trả danh sách dài — đều lọt.
    if not co("THIEU-THONG-TIN").get("con_thieu"):
        hong.append("THIEU-THONG-TIN: không sinh câu hỏi nào cho dữ liệu còn thiếu")
    if co("N4-PHU-HOP").get("con_thieu"):
        hong.append(
            "N4-PHU-HOP: hồ sơ đã đủ mà vẫn đòi bổ sung "
            f"{co('N4-PHU-HOP')['con_thieu']}"
        )

    # 7. Lý do loại — KHÔNG kiểm ở đây, có lý do.
    #
    # Đường `/public/matches` **cố ý** chỉ trả đơn đạt: ứng viên không cần một
    # danh sách những đơn mình trượt. Lý do loại nằm trong nhật ký giới thiệu và
    # chỉ nhân viên đọc được. Nên phép kiểm "chưa học tiếng thì lý do loại phải
    # là tiếng Nhật" cần đăng nhập, và nó nằm ở `scripts/e2e_hanh_trinh.py`.
    #
    # Ghi rõ chỗ không kiểm được còn hơn để người đọc tưởng bộ này phủ hết.

    # 8. Đường chi tiết một đơn phải khớp với danh sách.
    #
    # Nói đúng phạm vi: `/orders/{code}` đọc lại **cùng bản nhật ký** chứ không
    # đối chiếu lại từ đầu, nên phép này không chứng minh tính tất định của bộ
    # đối chiếu — việc đó là của `nghiem_thu_xuyen_suot`. Nó bắt một loại lỗi
    # khác: hai đường cùng đọc một bản ghi mà hiển thị khác nhau.
    rieng = co("DOI-DON").get("chi_tiet_khop") or []
    for ma_don, trong_ds, chi_tiet in rieng:
        if trong_ds != chi_tiet:
            hong.append(
                f"DOI-DON: {ma_don} trong danh sách là {trong_ds} "
                f"nhưng đường chi tiết trả {chi_tiet}"
            )
    return hong


def chay_ca(goc, ma, truong, nguyen_vong, *, hoi=False, engine_tat=False):
    hong = []
    k = Khach(goc)

    ma_s, phien = k.goi("/public/phien/moi", method="POST")
    if ma_s != 200 or not phien:
        return [f"không mở được phiên: {ma_s} {phien}"], {}
    sid = phien["session_id"]
    # Ghi danh NGAY, trước mọi lời gọi tạo dữ liệu: đây là căn cứ duy nhất để
    # `don_du_lieu_e2e` được xóa phiên này về sau. Xem `scripts/so_phien_e2e`.
    so_phien_e2e.ghi(sid, bo_do="e2e_xuyen_suot", url=goc)

    ma_s, _ = k.goi("/public/profiles", method="POST",
                    than={"mode": "manual", "fields": truong, "preferences": nguyen_vong})
    if ma_s == 429:
        # Bộ giới hạn theo IP: 20 lượt ghi hồ sơ mỗi 60 giây. Chạy bộ này ba lần
        # liền trong một phút là tự chặn mình. Nói rõ ra, vì "không tạo được hồ
        # sơ" đọc như một lỗi sản phẩm trong khi đây là chốt chặn đang chạy đúng.
        return ["bộ giới hạn theo IP đang chặn (429) — chờ 60 giây rồi chạy lại"], {}
    if ma_s != 201:
        return [f"không tạo được hồ sơ: {ma_s}"], {}

    ma_s, _ = k.goi(f"/public/profiles/{sid}/confirm", method="POST", than={"confirm": True})
    if ma_s not in (200, 201):
        hong.append(f"không xác nhận được hồ sơ: {ma_s}")

    ma_s, kq = k.goi(f"/public/matches/{sid}")
    if ma_s != 200:
        return hong + [f"không đối chiếu được: {ma_s} {kq}"], {}
    # Khoá là `matches`, không phải `items`: bản công khai chỉ gồm đơn đạt,
    # bản đầy đủ (kèm đơn trượt) nằm trong nhật ký cho nhân viên.
    muc = kq.get("matches") or []
    so_dat = len(muc)

    # Chốt "5/100": màn hình và lời giải thích phải cùng một quy tắc.
    for m in muc:
        if not m.get("score_ranked"):
            cau = (m.get("explanation_text") or "") + (m.get("explanation_block") or "")
            if "/100" in cau or "Xếp hạng" in cau:
                hong.append(f"{m['code']}: chưa xếp hạng được mà lời giải thích vẫn nói điểm/hạng")

    ma_s, tt = k.goi(f"/tu-van/v1/{sid}/tro-ly")
    if ma_s != 200:
        hong.append(f"không lấy được trạng thái trợ lý: {ma_s} {tt}")

    ma_s, md = k.goi(f"/tu-van/v1/{sid}/tro-ly/mo-dau", method="POST",
                     than={"moc": "sau_matching"})
    if ma_s != 200 or not (md or {}).get("reply"):
        hong.append(f"không dựng được lượt mở đầu: {ma_s}")
    cau_mo_dau = (md or {}).get("reply") or ""

    # Tải lại trang giữa cuộc: lượt mở đầu KHÔNG được nhân đôi.
    ma_s, md2 = k.goi(f"/tu-van/v1/{sid}/tro-ly/mo-dau", method="POST",
                      than={"moc": "sau_matching"})
    ma_s2, ls = k.goi(f"/tu-van/v1/{sid}/tro-ly/hoi")
    if ma_s2 == 200:
        so_mo_dau = sum(1 for l in (ls.get("items") or []) if "[hệ thống]" in (l.get("question") or ""))
        if so_mo_dau > 2:
            hong.append(f"tải lại trang nhân đôi lượt mở đầu ({so_mo_dau} lượt)")

    tra_loi = ""
    if hoi:
        cau = "Em có hợp đơn nào không ạ?"
        ma_s, ra = k.goi(f"/tu-van/v1/{sid}/tro-ly/hoi", method="POST",
                         than={"question": cau})
        if ma_s != 200:
            # Hết hạn mức KHÔNG được thành 500. Đây là trạng thái vận hành bình
            # thường của gói miễn phí (20 lượt/ngày/dự án/model), không phải sự cố.
            hong.append(f"hỏi trợ lý lỗi: {ma_s} {ra}")
        else:
            tra_loi = ra.get("answer") or ""
            if not tra_loi:
                hong.append("trợ lý trả về câu rỗng")
            if engine_tat:
                if ra.get("source") != "khong_goi_duoc":
                    hong.append(
                        f"engine tắt mà nguồn ghi là {ra.get('source')!r} — "
                        "thống kê sẽ tính hết hạn mức thành bot bí"
                    )
                # Câu khách vừa hỏi phải còn trong hội thoại. `add_turn` nằm sau
                # lời gọi mô hình và không có điều kiện; nếu nó rơi vào nhánh
                # thành công thì ngày hết hạn mức là ngày mất sạch câu hỏi, và
                # nhân viên đọc bàn giao sẽ không biết khách đã hỏi gì.
                _s, ls2 = k.goi(f"/tu-van/v1/{sid}/tro-ly/hoi")
                if cau not in json.dumps(ls2 or {}, ensure_ascii=False):
                    hong.append("engine tắt thì câu khách vừa hỏi biến mất khỏi hội thoại")

    ma_s, bg = k.goi(f"/tu-van/v1/{sid}/tro-ly/ban-giao")
    if ma_s != 200:
        hong.append(f"không dựng được bàn giao: {ma_s} {bg}")
    else:
        ban = (bg or {}).get("summary") or ""
        if "VIỆC NÊN LÀM TIẾP" not in ban:
            hong.append("bàn giao thiếu phần việc nên làm tiếp")
        if cau_mo_dau and "[hệ thống]" not in ban and so_dat and "ỨNG VIÊN ĐÃ HỎI" in ban:
            pass  # lượt hệ thống có thể bị lọc có chủ ý, không kết luận ở đây

    # Đường chi tiết một đơn phải khớp với danh sách — xem kỳ vọng số 8.
    chi_tiet_khop = []
    for m in muc[:3]:
        s_ct, ct = k.goi(f"/public/matches/{sid}/orders/{m['code']}")
        chi_tiet_khop.append(
            (
                m["code"],
                (m.get("eligible"), m.get("score"), m.get("score_ranked")),
                (
                    (ct or {}).get("eligible"),
                    (ct or {}).get("score"),
                    (ct or {}).get("score_ranked"),
                )
                if s_ct == 200
                else ("LOI", s_ct, None),
            )
        )

    return hong, {
        "sid": sid,
        "so_dat": so_dat,
        "mo_dau": cau_mo_dau,
        "tra_loi": tra_loi,
        # Dữ liệu thô cho `ky_vong_rieng`. Thu ở đây, chấm ở đó — cùng lý do như
        # `nghiem_thu_agent`: phép đo và phép chấm tách nhau thì sửa cách chấm
        # không phải đo lại.
        "muc": muc,
        "con_thieu": kq.get("missing_info") or [],
        "chi_tiet_khop": chi_tiet_khop,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8020")
    ap.add_argument("--hoi", action="store_true", help="gọi mô hình thật một lượt (tốn hạn mức)")
    ap.add_argument(
        "--engine-tat",
        action="store_true",
        help=(
            "máy chủ đang chạy với ADVISOR_ENABLED=false — đo nhánh hết hạn mức. "
            "Kèm --hoi thì hỏi cả năm ca mà KHÔNG tốn hạn mức nào, vì không lượt "
            "nào ra tới Gemini."
        ),
    )
    args = ap.parse_args()

    ma_s, _ = Khach(args.url).goi("/health")
    if ma_s != 200:
        print(f"Backend không trả lời ở {args.url} — bỏ qua.")
        return 2

    print(f"E2E xuyên suốt qua HTTP · {args.url}")
    if args.engine_tat:
        print("Engine tư vấn: TẮT trên máy chủ — đo nhánh hết hạn mức")
    print(f"Gọi mô hình thật: {'CÓ' if args.hoi and not args.engine_tat else 'không'}")
    print()

    tong = 0
    ket: dict = {}
    for i, (ma, truong, nv) in enumerate(CA):
        hong, so = chay_ca(
            args.url, ma, truong, nv,
            hoi=args.hoi and (args.engine_tat or i == 0),
            engine_tat=args.engine_tat,
        )
        ket[ma] = so
        tong += len(hong)
        print(f"[{'ĐẠT ' if not hong else 'HỎNG'}] {ma} · {so.get('so_dat', '?')} đơn đạt · {so.get('sid', '')[:8]}")
        if so.get("mo_dau"):
            print(f"   mở đầu: {so['mo_dau'][:120]}…")
        if so.get("tra_loi"):
            print(f"   trợ lý: {so['tra_loi'][:200]}…")
        for h in hong:
            print(f"   ! {h}")

    print()
    print("--- Kỳ vọng riêng từng ca (so sánh chéo giữa năm hồ sơ)")
    rieng = ky_vong_rieng(ket)
    for h in rieng:
        print(f"   ! {h}")
    if not rieng:
        print("   tám kỳ vọng đều đúng")
    tong += len(rieng)

    print()
    print("=" * 72)
    print(f"TỔNG: {len(CA)} ca · {tong} chỗ hỏng")
    return 1 if tong else 0


if __name__ == "__main__":
    raise SystemExit(main())
