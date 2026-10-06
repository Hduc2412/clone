# -*- coding: utf-8 -*-
"""Một hành trình đầy đủ, qua HTTP thật, từ CV mẫu tới lúc nhân viên nhận việc.

    venv/Scripts/python.exe -m scripts.e2e_hanh_trinh [--url http://127.0.0.1:8020]

## Bộ này trả lời câu nào

`e2e_xuyen_suot.py` chạy năm hồ sơ nhưng **bỏ qua bốn mắt xích**: gửi CV, đăng ký
đơn, tạo lịch hẹn, và nhân viên nhận xử lý. Nó chứng minh phần tư vấn đúng, không
chứng minh cả chuỗi giá trị đúng.

Chuỗi ấy là chính đề tài:

    gửi CV -> máy đọc hồ sơ -> trợ lý hỏi phần thiếu -> khách xác nhận
      -> đối chiếu đơn -> đăng ký + chọn khung giờ -> nhân viên nhận đúng mọi thứ

Mắt xích cuối dễ hỏng nhất và khó thấy nhất, vì nó chỉ hỏng ở tầng **dữ liệu đi
qua nhiều lần ghi**: bản bàn giao dựng trước khi lịch hẹn tồn tại, liên kết lịch
mất khi một lời ghi thất bại, hội thoại chỉ gom một phạm vi. Cả ba đều đã gặp
thật, và không bộ đo nào trong tiến trình thấy được.

## Dữ liệu dùng

CV mẫu trong `tests/fixtures/cv/` — **tên và số liệu đều là giả**, sinh ra để
kiểm thử, không phải hồ sơ của người thật. Đáp án nằm ở `dap_an.json`.

## Tốn gì

Đúng **một lượt gọi mô hình** cho bước đọc CV. Mọi bước khác dựng bằng quy tắc.
Thêm `--hoi` để hỏi trợ lý một câu thật (một lượt nữa).

## Tài khoản nhân viên

Script tự tạo **hai** nhân viên tư vấn tạm, vai trò `consultant`, rồi **xóa khi
xong**. Không dùng admin: admin vượt qua mọi chốt phân quyền, nên một bộ đo chạy
bằng admin không thể thấy nhân viên thường có làm được việc của mình hay không.
Và phép "người thứ hai bấm nhận" phải là một người khác thật.
"""
import argparse
import asyncio
import io
import json
import mimetypes
import urllib.error
import urllib.request
import uuid
from datetime import timedelta
from pathlib import Path

import app  # noqa: F401 — đặt stdout về UTF-8
from scripts import so_phien_e2e
from app.core.timeutil import local_today

CV_DIR = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "cv"
CV_FILE = "07_tran_thi_thu_ha.pdf"

#: Hai nhân viên tư vấn tạm, vai trò `consultant`. Script tự tạo và tự xóa.
NHAN_VIEN = (
    ("e2e-tu-van-a@local.test", "E2eTuVanA!2026"),
    ("e2e-tu-van-b@local.test", "E2eTuVanB!2026"),
)

#: Quản lý tạm — chỉ để làm đúng một việc của quản lý: chuyển hồ sơ từ A sang B.
QUAN_LY = ("e2e-quan-ly@local.test", "E2eQuanLy!2026")

# Những trường quyết định ai bị loại. Máy đọc sai ở đây là loại oan người thật,
# nên chúng được kiểm riêng thay vì chấm chung một tỉ lệ phần trăm.
TRUONG_QUYET_DINH = ("japanese_level", "education_level", "birth_year")

#: Mã thoát khi bước cần mô hình không chạy được. Khác 0 (đạt) và 1 (hỏng), để
#: `scripts.dot_bien` không đếm một lần Gemini quá tải thành một đột biến bị bắt.
KHONG_DO_DUOC = 3


class Khach:
    """Một người dùng: giữ cookie y như trình duyệt."""

    def __init__(self, goc: str) -> None:
        self.goc = goc.rstrip("/")
        self.cookie: dict[str, str] = {}

    def _gui(self, req):
        if self.cookie:
            req.add_header(
                "Cookie", "; ".join(f"{k}={v}" for k, v in self.cookie.items())
            )
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                dat = r.read().decode("utf-8")
                for h in r.headers.get_all("Set-Cookie") or ():
                    cap = h.split(";", 1)[0]
                    if "=" in cap:
                        ten, gt = cap.split("=", 1)
                        self.cookie[ten] = gt
                return r.status, (json.loads(dat) if dat else None)
        except urllib.error.HTTPError as e:
            than = e.read().decode("utf-8")
            try:
                return e.code, json.loads(than or "{}")
            except ValueError:
                return e.code, {"raw": than[:300]}

    def goi(self, duong, *, method="GET", than=None):
        req = urllib.request.Request(
            f"{self.goc}{duong}",
            method=method,
            data=None if than is None else json.dumps(than).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        return self._gui(req)

    def gui_file(self, duong, duong_file: Path):
        """multipart/form-data dựng tay — không thêm thư viện cho một lời gọi."""
        ranh = f"----e2e{uuid.uuid4().hex}"
        kieu = mimetypes.guess_type(duong_file.name)[0] or "application/octet-stream"
        than = io.BytesIO()
        than.write(f"--{ranh}\r\n".encode())
        than.write(
            f'Content-Disposition: form-data; name="file"; '
            f'filename="{duong_file.name}"\r\n'.encode()
        )
        than.write(f"Content-Type: {kieu}\r\n\r\n".encode())
        than.write(duong_file.read_bytes())
        than.write(f"\r\n--{ranh}--\r\n".encode())
        req = urllib.request.Request(
            f"{self.goc}{duong}",
            method="POST",
            data=than.getvalue(),
            headers={"Content-Type": f"multipart/form-data; boundary={ranh}"},
        )
        return self._gui(req)


# --- Tài khoản nhân viên tạm -------------------------------------------------


async def _tao_nhan_vien() -> list[str]:
    """Tạo hai nhân viên tư vấn tạm. Trả danh sách email **chính script này** tạo.

    Chỉ xóa về sau những email có trong danh sách trả về: tài khoản đã có sẵn từ
    trước (lần chạy bị ngắt giữa chừng chẳng hạn) thì dùng lại, không xóa.
    """
    from app.auth.security import hash_password
    from app.db.common import get_db
    from app.db.database import close_db, create_staff_user, init_db

    await init_db()
    da_tao = []
    try:
        for email, mk, vai in [(e, m, "consultant") for e, m in NHAN_VIEN] + [(*QUAN_LY, "manager")]:
            if await get_db().staff_users.count_documents({"email": email}):
                continue
            await create_staff_user(
                {
                    "full_name": f"Nhân viên E2E {email[11]} (tạm)",
                    "email": email,
                    "role": vai,
                    "password_hash": hash_password(mk),
                }
            )
            da_tao.append(email)
        return da_tao
    finally:
        await close_db()


async def _xoa_nhan_vien(emails: list[str]) -> int:
    """Xóa đúng những tài khoản tạm đã tạo. Không xóa gì khác."""
    from app.db.common import get_db
    from app.db.database import close_db, init_db

    if not emails:
        return 0
    await init_db()
    try:
        ra = await get_db().staff_users.delete_many({"email": {"$in": list(emails)}})
        return ra.deleted_count
    finally:
        await close_db()


def _ghi(*phan):
    print("   " + " ".join(str(x) for x in phan))


# --- Phần của khách ---------------------------------------------------------


def chay(goc: str, *, hoi: bool, khai_tay: bool = False) -> tuple[list[str], dict]:
    hong: list[str] = []
    so: dict = {}
    k = Khach(goc)

    # 1. Phiên mới
    ma_s, phien = k.goi("/public/phien/moi", method="POST")
    if ma_s != 200:
        return [f"không mở được phiên: {ma_s}"], so
    sid = phien["session_id"]
    # Ghi danh NGAY, trước mọi lời gọi tạo dữ liệu: đây là căn cứ duy nhất để
    # `don_du_lieu_e2e` được xóa phiên này về sau. Xem `scripts/so_phien_e2e`.
    so_phien_e2e.ghi(sid, bo_do="e2e_hanh_trinh", url=goc)
    so["sid"] = sid
    _ghi(f"1. phiên {sid[:8]}…")

    # 2. Gửi CV — hoặc khai tay khi không được gọi mô hình
    if khai_tay:
        return _phan_sau_khai_tay(k, sid, so, hoi=hoi)

    duong_cv = CV_DIR / CV_FILE
    if not duong_cv.exists():
        return [f"không thấy CV mẫu {duong_cv}"], so
    ma_s, ra = k.gui_file(f"/public/documents/{sid}", duong_cv)
    if ma_s not in (200, 201, 202):
        return hong + [f"gửi CV lỗi: {ma_s} {ra}"], so
    truong = ((ra or {}).get("profile") or {}).get("fields") or {}
    doc_duoc = {t: v.get("value") for t, v in truong.items() if isinstance(v, dict)}
    _ghi(f"2. CV {CV_FILE} → máy đọc {len(doc_duoc)} trường: {sorted(doc_duoc)}")

    # Máy không đọc được trường nào = mô hình không trả lời, KHÔNG phải mã sai.
    #
    # CV mẫu này luôn đọc ra chín trường khi mô hình chạy. Ra số không thì gần
    # như chắc chắn là 503 hoặc hết hạn mức. Báo "hỏng" lúc ấy là trộn hai thứ
    # khác hẳn nhau — và nó làm hỏng cả phép đột biến: một đột biến bị đánh dấu
    # BẮT ĐƯỢC chỉ vì Gemini đang quá tải.
    #
    # Nên dừng với mã thoát riêng (`KHONG_DO_DUOC`), cùng nguyên tắc với
    # `nghiem_thu_agent`: ca không gọi được mô hình thì không ghi kết quả.
    if not doc_duoc:
        so["khong_do_duoc"] = (
            f"máy không đọc được trường nào từ CV ({(ra or {}).get('message')!r}) — "
            "nhiều khả năng mô hình đang quá tải hoặc hết hạn mức"
        )
        return hong, so

    so["co_cv"] = True
    hong += _cham_doc_cv(doc_duoc, truong)

    # 3. Lượt mở đầu sau khi đọc CV
    ma_s, md = k.goi(
        f"/tu-van/v1/{sid}/tro-ly/mo-dau", method="POST", than={"moc": "sau_cv"}
    )
    cau = (md or {}).get("reply") or ""
    if ma_s != 200 or not cau:
        hong.append(f"không dựng được lượt mở đầu sau CV: {ma_s}")
    else:
        _ghi(f"3. trợ lý: {cau[:110]}…")
        # Không được kể ra một trình độ máy KHÔNG đọc được. Đây là chỗ dễ bịa
        # nhất của lượt mở đầu, vì nó liệt kê lại hồ sơ cho khách kiểm.
        for muc in ("N5", "N4", "N3", "N2", "N1"):
            if muc in cau and doc_duoc.get("japanese_level") != muc:
                hong.append(
                    f"lượt mở đầu nói {muc} trong khi máy đọc ra "
                    f"{doc_duoc.get('japanese_level')!r}"
                )
    so["mo_dau_cv"] = cau

    # 4. Khách bổ sung phần còn thiếu
    bo_sung = {}
    if "experience_years" not in doc_duoc:
        bo_sung["experience_years"] = 2
    if "care_experience" not in doc_duoc:
        bo_sung["care_experience"] = True

    # Số điện thoại: đổi sang một số **chưa ai dùng** cho mỗi lần chạy.
    #
    # Khách hàng được dựng lại theo số điện thoại đã chuẩn hóa, và một số chỉ
    # được có một hồ sơ đăng ký đang xử lý. Lần chạy thứ hai của bộ này dùng lại
    # số trong CV mẫu nên bị chặn với 409 *"Bạn đang có một hồ sơ đang được xử
    # lý"* — **đó là chốt chặn đang chạy đúng**, không phải lỗi.
    #
    # Nhưng một bộ đo chỉ chạy được một lần là một bộ đo gần như vô dụng. Nên
    # đổi số là việc khách làm thật (sửa lại số trong CV) và nó giữ nguyên ý
    # nghĩa của phép đo. Phép kiểm chống trùng vẫn còn: nó bấm đăng ký hai lần
    # trong **cùng** một lần chạy.
    so["phone"] = f"09{uuid.uuid4().int % 100000000:08d}"
    bo_sung["phone"] = so["phone"]
    ma_s, _ = k.goi(
        f"/public/profiles/{sid}",
        method="PATCH",
        than={
            "fields": bo_sung,
            "preferences": {
                "desired_prefecture": "Tokyo",
                "desired_region_group": "kanto",
                "desired_employer_type": "vien_duong_lao",
            },
        },
    )
    if ma_s != 200:
        hong.append(f"không bổ sung được hồ sơ: {ma_s}")

    # Dữ liệu CV KHÔNG được mất khi khách sửa một phần khác.
    #
    # Lỗi `preferences=None` xóa trắng hồ sơ (gặp thật 05/10) nằm đúng ở đây, và
    # nó từng trả 500 trong khi màn hình chỉ nói "Không kết nối được máy chủ".
    ma_s, sau = k.goi(f"/public/profiles/{sid}")
    con = {
        t: v.get("value")
        for t, v in ((sau or {}).get("fields") or {}).items()
        if isinstance(v, dict)
    }
    mat = [t for t in doc_duoc if t not in con]
    if mat:
        hong.append(f"bổ sung hồ sơ làm MẤT trường máy đã đọc: {mat}")
    _ghi(f"4. khách bổ sung {sorted(bo_sung)} + nguyện vọng → hồ sơ còn {len(con)} trường")
    # Tên ĐÚNG NHƯ TRONG HỒ SƠ — để kiểm phiếu tóm tắt về sau. Không dùng cách viết
    # trong đáp án: CV mẫu in tên bằng chữ hoa, máy đọc giữ nguyên ("TRẦN THỊ THU
    # HÀ") kèm chứng cứ, còn đáp án viết thường. Lượt chốt 06/10 14:23 báo "phiếu
    # thiếu tên" vì so với đáp án — phiếu đúng, bộ đo sai.
    so["ten_ho_so"] = con.get("full_name")

    # 5. Xác nhận hồ sơ
    ma_s, _ = k.goi(
        f"/public/profiles/{sid}/confirm", method="POST", than={"confirm": True}
    )
    if ma_s not in (200, 201):
        return hong + [f"không xác nhận được hồ sơ: {ma_s}"], so

    # 6. Đối chiếu
    ma_s, kq = k.goi(f"/public/matches/{sid}")
    if ma_s != 200:
        return hong + [f"không đối chiếu được: {ma_s} {kq}"], so
    muc = kq.get("matches") or []
    if not muc:
        return hong + ["không có đơn nào đạt — hồ sơ này lẽ ra nộp được"], so
    nhat = next((m for m in muc if m.get("rank") == 1), muc[0])
    so["don"] = nhat["code"]
    _ghi(
        f"5. đối chiếu: {len(muc)} đơn đạt, hạng 1 là {nhat['code']} "
        f"({nhat.get('prefecture')})"
    )

    if hoi:
        ma_s, ra = k.goi(
            f"/tu-van/v1/{sid}/tro-ly/hoi",
            method="POST",
            than={"question": "Em còn thiếu gì để nộp đơn này ạ?"},
        )
        if ma_s == 200:
            so["tra_loi"] = ra.get("answer") or ""
            so["nguon_tra_loi"] = ra.get("source")
            _ghi(f"   trợ lý [{ra.get('source')}]: {so['tra_loi'][:160]}…")
            if ra.get("source") == "khong_goi_duoc":
                # Mô hình không trả lời (hết hạn mức, quá tải, quá giờ chờ). Câu
                # khách nhận là câu ghép sẵn "trợ lý đang bận" — tức là CHẤT LƯỢNG
                # TƯ VẤN CHƯA ĐƯỢC ĐO. Lượt chốt 06/10 14:31 báo ĐẠT đúng trong
                # tình huống này: model chính hết giờ chờ, model dự phòng 503, mà
                # bộ đo chỉ kiểm câu trả lời không rỗng.
                so.setdefault("khong_do", []).append(
                    "hỏi trợ lý: mô hình không trả lời (khong_goi_duoc) — "
                    "chất lượng tư vấn bằng mô hình thật CHƯA được đo ở lượt này"
                )
        else:
            hong.append(f"hỏi trợ lý lỗi: {ma_s}")

    # 7. Đăng ký đơn, kèm hai chốt chặn
    hong += _dang_ky(k, sid, nhat["code"], so)

    # 8. Xin gặp mặt kèm khung giờ
    hong += _xin_gap(k, sid, nhat["code"], so)
    return hong, so


def _phan_sau_khai_tay(k: "Khach", sid: str, so: dict, *, hoi: bool):
    """Đi hết hành trình mà **không gọi mô hình**: khai hồ sơ tay thay cho đọc CV.

    ## Vì sao cần chế độ này

    Bước đọc CV tốn một lượt gọi mô hình, và hạn mức là 20 lượt/ngày/model. Ngày
    06/10 một lượt đột biến đầy đủ đã chạy bộ hành trình sáu lần, và đến lượt
    thứ bảy thì máy chủ trả 429 cả ba lần thử — bộ đo dừng ở bước 2 và mọi bước
    sau (đăng ký, lịch hẹn, bấm gửi lại, nhân viên nhận) không được đo.

    Nhưng bốn bước ấy **không dính gì tới mô hình**. Để chúng phụ thuộc hạn mức
    chỉ vì chúng đứng sau bước đọc CV là để một ràng buộc vận hành chặn mất một
    phép đo không liên quan. Khai tay bằng đúng dữ liệu trong `dap_an.json` thì
    hồ sơ giống hệt hồ sơ máy đọc ra, và phần sau đo được bất cứ lúc nào.

    Cái giá: chế độ này **không** đo bước đọc CV và lượt mở đầu sau CV. Bản tổng
    kết ghi rõ điều đó.
    """
    hong: list[str] = []
    da = json.loads((CV_DIR / "dap_an.json").read_text(encoding="utf-8"))
    mong = next(e for e in da if e.get("file") == CV_FILE)["expected"]
    nguyen_vong_khoa = {"desired_prefecture", "desired_employer_type"}
    truong = {t: v for t, v in mong.items() if t not in nguyen_vong_khoa}
    so["phone"] = f"09{uuid.uuid4().int % 100000000:08d}"
    truong["phone"] = so["phone"]

    ma_s, _ = k.goi(
        "/public/profiles",
        method="POST",
        than={
            "mode": "manual",
            "fields": truong,
            "preferences": {
                "desired_prefecture": "Tokyo",
                "desired_region_group": "kanto",
                "desired_employer_type": "vien_duong_lao",
            },
        },
    )
    if ma_s != 201:
        return [f"khai tay hồ sơ lỗi: {ma_s}"], so
    _ghi(f"2. KHAI TAY từ đáp án {CV_FILE}: {len(truong)} trường (bỏ qua bước đọc CV)")
    so["ten_ho_so"] = truong.get("full_name")

    ma_s, _ = k.goi(f"/public/profiles/{sid}/confirm", method="POST", than={"confirm": True})
    if ma_s not in (200, 201):
        return hong + [f"không xác nhận được hồ sơ: {ma_s}"], so

    ma_s, kq = k.goi(f"/public/matches/{sid}")
    if ma_s != 200:
        return hong + [f"không đối chiếu được: {ma_s} {kq}"], so
    muc = kq.get("matches") or []
    if not muc:
        return hong + ["không có đơn nào đạt — hồ sơ này lẽ ra nộp được"], so
    nhat = next((m for m in muc if m.get("rank") == 1), muc[0])
    so["don"] = nhat["code"]
    _ghi(f"5. đối chiếu: {len(muc)} đơn đạt, hạng 1 là {nhat['code']} ({nhat.get('prefecture')})")

    hong += _dang_ky(k, sid, nhat["code"], so)
    hong += _xin_gap(k, sid, nhat["code"], so)
    return hong, so


def _cham_doc_cv(doc_duoc: dict, truong: dict) -> list[str]:
    """Chấm bước đọc CV trên những trường quyết định ai bị loại."""
    hong = []
    dap_an_file = CV_DIR / "dap_an.json"
    if not dap_an_file.exists():
        return ["không thấy dap_an.json — bước đọc CV không chấm được"]

    # `dap_an.json` là một DANH SÁCH, mỗi phần tử `{file, expected, note, …}`.
    # Bản đầu của bộ này gọi `.get(CV_FILE)` trên nó như một từ điển — và nếu
    # không có `assert` thì nó lặng lẽ không chấm gì cả.
    da = json.loads(dap_an_file.read_text(encoding="utf-8"))
    muc = next((e for e in da if e.get("file") == CV_FILE), None)
    if muc is None:
        return [f"dap_an.json không có mục nào cho {CV_FILE}"]
    mong = muc.get("expected") or {}
    if not mong:
        return [f"dap_an.json: mục {CV_FILE} không có `expected`"]
    for t in TRUONG_QUYET_DINH:
        if t in mong and doc_duoc.get(t) != mong[t]:
            hong.append(f"CV: {t} đọc ra {doc_duoc.get(t)!r}, đáp án là {mong[t]!r}")

    # Nguồn phải là `cv`: chưa ai xác nhận gì. Một trường mang `user_confirmed`
    # ngay sau khi gửi CV là hệ thống tự nhận thay khách.
    sai = [
        t
        for t, v in truong.items()
        if isinstance(v, dict) and v.get("source") not in (None, "cv")
    ]
    if sai:
        hong.append(f"CV: trường {sai} mang nguồn khác `cv` dù chưa ai xác nhận")
    return hong


def _dang_ky(k: Khach, sid: str, ma_don: str, so: dict) -> list[str]:
    hong = []

    # `confirmed=false` phải bị từ chối, và phép kiểm này phải chạy **TRƯỚC** lần
    # đăng ký thật.
    #
    # Thứ tự không phải chuyện gọn gàng. Bản đầu kiểm nó sau cùng, và phép đột
    # biến "bỏ chốt chặn confirmed" **lọt qua**: lúc ấy khách đã có hồ sơ cho đơn
    # này rồi, nên lời gọi trả 409 vì trùng chứ không phải vì thiếu xác nhận. Một
    # chốt chặn bị che bởi một chốt chặn khác thì không ai canh nó nữa.
    ma_s, _ = k.goi(
        f"/public/registrations/{sid}",
        method="POST",
        than={"job_order_code": ma_don, "confirmed": False},
    )
    if ma_s == 201:
        hong.append("đăng ký được tạo dù khách CHƯA xác nhận")

    ma_s, dk = k.goi(
        f"/public/registrations/{sid}",
        method="POST",
        than={"job_order_code": ma_don, "confirmed": True},
    )
    if ma_s != 201:
        hong.append(f"đăng ký đơn lỗi: {ma_s} {dk}")
    else:
        so["ho_so_tuyen"] = dk.get("application_code")
        _ghi(f"6. đăng ký {ma_don} → hồ sơ tuyển {so['ho_so_tuyen']}")

    # Bấm hai lần không tạo hai hồ sơ.
    ma_s, _ = k.goi(
        f"/public/registrations/{sid}",
        method="POST",
        than={"job_order_code": ma_don, "confirmed": True},
    )
    if ma_s == 429:
        # Bộ giới hạn tần suất (5 lượt đăng ký / 5 phút / IP) chặn TRƯỚC khi tới
        # phép chống trùng. Lần bấm thứ hai có bị chặn — nhưng không phải bởi thứ
        # ta đang đo. Hai lượt chạy liền nhau gặp đúng chuyện này ngày 06/10.
        so.setdefault("khong_do", []).append(
            "chống đăng ký trùng: bộ giới hạn tần suất chặn trước (429) — chờ 5 phút rồi chạy lại"
        )
    elif ma_s not in (400, 409):
        hong.append(f"đăng ký trùng không bị chặn: trả {ma_s}")

    return hong


def _xin_gap(k: Khach, sid: str, ma_don: str, so: dict) -> list[str]:
    hong = []
    ngay = local_today() + timedelta(days=3)
    while ngay.weekday() == 6:  # Chủ Nhật không nhận lịch
        ngay += timedelta(days=1)
    than = {
            "kind": "gap_mat",
            "full_name": "Trần Thị Thu Hà",
            # Cùng số với hồ sơ: hai bên phải là CÙNG một người, nếu không
            # thì phép kiểm "nhân viên nhận đúng hồ sơ" mất ý nghĩa.
            "phone": so.get("phone") or f"09{uuid.uuid4().int % 100000000:08d}",
            "message": "Em muốn gặp để hỏi thêm về đơn này.",
            "job_order_code": ma_don,
            "appointment_date": ngay.isoformat(),
            "appointment_time": "14:00",
            "meeting_kind": "truc_tiep",
    }
    ma_s, ht = k.goi(f"/tu-van/v1/{sid}/ho-tro", method="POST", than=than)
    if ma_s != 201:
        return [f"gửi yêu cầu hỗ trợ lỗi: {ma_s} {ht}"]
    so["ho_tro"] = ht.get("code")
    so["lich"] = ht.get("appointment_code")
    if not so["lich"]:
        hong.append("chọn khung giờ mà không sinh được lịch hẹn")
    _ghi(f"7. yêu cầu {so['ho_tro']} · lịch {so['lich']} · {ngay} 14:00")

    # Khách bấm gửi LẦN HAI — mạng chậm, hoặc lần đầu màn hình báo lỗi.
    #
    # Phải nhận lại **đúng mã yêu cầu và đúng mã lịch** của lần đầu. Không được
    # tạo việc thứ hai cho nhân viên, và không được nói "khung giờ chưa thành
    # lịch hẹn" về một lịch đã có thật. Đây là tình huống bản rà soát 06/10 nêu:
    # khách tưởng chưa gửi được rồi bấm lại.
    ma_s2, ht2 = k.goi(f"/tu-van/v1/{sid}/ho-tro", method="POST", than=than)
    if ma_s2 != 201:
        hong.append(f"bấm gửi lần hai bị từ chối: {ma_s2} {ht2}")
    else:
        if (ht2 or {}).get("code") != so["ho_tro"]:
            hong.append(
                f"bấm gửi lần hai tạo yêu cầu MỚI {(ht2 or {}).get('code')} "
                f"thay vì trả lại {so['ho_tro']}"
            )
        if (ht2 or {}).get("appointment_code") != so["lich"]:
            hong.append(
                f"bấm gửi lần hai trả lịch {(ht2 or {}).get('appointment_code')!r} "
                f"thay vì lịch đã có {so['lich']!r} — màn hình sẽ báo khách là "
                "khung giờ chưa thành lịch hẹn"
            )
        else:
            _ghi("   bấm gửi lần hai → cùng yêu cầu, cùng lịch")
    return hong


# --- Phần của nhân viên -----------------------------------------------------
#
# HAI tài khoản `consultant` riêng, không tài khoản admin nào.
#
# Bản trước dùng một tài khoản admin, và phép "người thứ hai bấm nhận" thực ra
# là CÙNG tài khoản bấm hai lần. Hai lỗi đo cùng lúc:
#
# - Admin vượt qua mọi chốt phân quyền (`can_access`, `is_privileged`), nên bộ
#   đo không thể thấy một nhân viên thường có làm được việc của mình hay không.
# - Cùng một người bấm hai lần chỉ chứng minh "không nhận lại được việc đã
#   nhận", không chứng minh "hai người không giành được cùng một việc".
#
# Chủ đồ án chỉ ra cả hai ngày 06/10.


def phan_nhan_vien(goc: str, so: dict) -> list[str]:
    """Hai nhân viên tư vấn: A nhận việc, B đến sau. Mỗi người phải thấy đúng phần mình."""
    hong: list[str] = []
    a = Khach(goc)
    b = Khach(goc)
    for nv, (email, mk) in ((a, NHAN_VIEN[0]), (b, NHAN_VIEN[1])):
        ma_s, ra = nv.goi("/auth/login", method="POST", than={"email": email, "password": mk})
        if ma_s != 200:
            return [f"{email} không đăng nhập được: {ma_s}"]
        vai = ((ra or {}).get("user") or {}).get("role")
        if vai != "consultant":
            # Đăng nhập được bằng vai trò khác thì mọi phép đo phân quyền phía
            # sau đều vô nghĩa — dừng ngay thay vì báo đạt.
            return [f"{email} đăng nhập với vai trò {vai!r}, không phải consultant"]
    _ghi(f"8. hai nhân viên tư vấn đăng nhập: {NHAN_VIEN[0][0]}, {NHAN_VIEN[1][0]}")

    hong += _hang_doi_ho_tro(a, b, so)
    hong += _doc_yeu_cau(a, so)
    hong += _nhan_ho_tro(a, b, so)
    hong += _nhan_ho_so_tuyen(a, b, so)
    hong += _phieu_tom_tat(a, b, so)
    hong += _ho_so_ung_vien(a, b, so)
    hong += _nhat_ky_gioi_thieu(a, b, so)
    hong += _khong_co_quyen_quan_ly(a, so)
    hong += _chuyen_ho_so(goc, a, b, so)
    return hong


def _chuyen_ho_so(goc: str, a: Khach, b: Khach, so: dict) -> list[str]:
    """Quản lý chuyển hồ sơ từ A sang B: quyền đọc hồ sơ VÀ nhật ký phải đi theo.

    Kịch bản chủ đồ án tái hiện ngày 06/10. Trước bản sửa: A mất quyền xem hồ sơ
    nhưng VẪN đọc được nhật ký cũ; B xem được hồ sơ nhưng nhật ký trả 403 — vì
    quyền đọc nhật ký dựa vào `assigned_to` của chính nhật ký, một ảnh chụp lúc
    đối chiếu.

    Với từng người, ba câu hỏi phải cùng một đáp án: xem được hồ sơ không, đọc
    được nhật ký không, nhật ký có trong danh sách của mình không.
    """
    ma, ma_hs, ma_nk = so.get("ho_so_tuyen"), so.get("ma_ho_so_ung_vien"), so.get("ma_nhat_ky")
    if not (ma and ma_hs and ma_nk):
        return [f"thiếu dữ liệu để kiểm chuyển hồ sơ (đơn={ma}, hồ sơ={ma_hs}, nhật ký={ma_nk})"]
    ql = Khach(goc)
    ma_s, _ = ql.goi("/auth/login", method="POST", than={"email": QUAN_LY[0], "password": QUAN_LY[1]})
    if ma_s != 200:
        return [f"quản lý tạm không đăng nhập được: {ma_s}"]
    ma_s, ra = ql.goi(
        f"/registrations/{ma}/handover",
        method="POST",
        than={"assigned_to": NHAN_VIEN[1][0], "note": "E2E: chuyển A sang B"},
    )
    if ma_s != 200:
        return [f"quản lý chuyển hồ sơ {ma} sang B lỗi: {ma_s} {ra}"]

    hong = []
    for ten, nv, phai in (("A", a, False), ("B", b, True)):
        s_hs, _ = nv.goi(f"/profiles/{ma_hs}")
        s_nk, _ = nv.goi(f"/recommendation-logs/{ma_nk}")
        _s, ds = nv.goi(f"/recommendation-logs?session_id={so['sid']}&limit=5")
        trong_ds = ma_nk in {i.get("code") for i in (ds if isinstance(ds, list) else [])}
        for vat, co in (("hồ sơ", s_hs == 200), ("nhật ký", s_nk == 200), ("nhật ký trong danh sách", trong_ds)):
            if co != phai:
                hong.append(
                    f"sau khi chuyển A → B, {ten} {'không ' if phai else 'vẫn '}thấy được {vat}"
                    f" (hồ sơ {s_hs}, nhật ký {s_nk})"
                )
    if not hong:
        _ghi("16. quản lý chuyển A → B: B xem được hồ sơ và nhật ký · A mất cả hai")
    return hong


def _cac_ma(ra) -> set:
    ds = ra if isinstance(ra, list) else ((ra or {}).get("items") or [])
    return {i.get("code") or i.get("application_code") for i in ds}


def _hang_doi_ho_tro(a: Khach, b: Khach, so: dict) -> list[str]:
    """Việc chưa ai nhận thì CẢ HAI phải thấy — không thì không ai nhận được."""
    hong = []
    for ten, nv in (("A", a), ("B", b)):
        ma_s, ra = nv.goi("/ho-tro")
        if ma_s != 200:
            hong.append(f"nhân viên {ten} không đọc được hàng đợi hỗ trợ: {ma_s}")
        elif so["ho_tro"] not in _cac_ma(ra):
            hong.append(f"nhân viên {ten} không thấy yêu cầu {so['ho_tro']} trong hàng đợi")
    if not hong:
        _ghi(f"9. cả hai thấy {so['ho_tro']} trong hàng đợi hỗ trợ")
    return hong


def _doc_yeu_cau(nv: Khach, so: dict) -> list[str]:
    """Chi tiết yêu cầu phải mang lịch hẹn và bản bàn giao đủ dữ liệu."""
    hong = []
    ma_s, ct = nv.goi(f"/ho-tro/{so['ho_tro']}")
    if ma_s != 200:
        return [f"nhân viên A không đọc được yêu cầu: {ma_s} {ct}"]
    yc = (ct or {}).get("request") or {}
    lich = (ct or {}).get("appointment")

    if lich is None:
        hong.append("chi tiết yêu cầu không mang lịch hẹn dù khách đã chọn giờ")
    elif lich.get("appointment_code") != so.get("lich"):
        hong.append(
            f"lịch trả về {lich.get('appointment_code')} khác lịch đã tạo {so.get('lich')}"
        )

    ban = yc.get("ban_giao") or ""
    if not ban:
        hong.append("yêu cầu không mang bản bàn giao")
    else:
        # Bốn thứ nhân viên BẮT BUỘC thấy trước khi bấm số.
        for nhan, can in (
            ("đơn khách chọn", so.get("don") or ""),
            ("khung giờ khách chọn", "14:00"),
            ("việc nên làm tiếp", "VIỆC NÊN LÀM TIẾP"),
            ("khối lịch hẹn", "KHUNG GIỜ"),
        ):
            if can and can not in ban:
                hong.append(f"bản bàn giao thiếu {nhan} ({can!r})")
    _ghi(
        f"10. A đọc {so['ho_tro']}: bàn giao {len(ban)} ký tự, "
        f"lịch {(lich or {}).get('appointment_code')}"
    )
    return hong


def _nhan_ho_tro(a: Khach, b: Khach, so: dict) -> list[str]:
    hong = []
    ma_s, nhan = a.goi(f"/ho-tro/{so['ho_tro']}/nhan", method="POST")
    if ma_s != 200:
        return [f"A nhận yêu cầu hỗ trợ lỗi: {ma_s} {nhan}"]
    if (nhan or {}).get("assigned_to") != NHAN_VIEN[0][0]:
        hong.append(f"A nhận xong mà người phụ trách là {(nhan or {}).get('assigned_to')!r}")

    # B — một NGƯỜI KHÁC — bấm nhận cùng việc: phải 409, và câu trả lời phải
    # nói ai đang giữ, để B biết hỏi ai thay vì bấm lại.
    ma_s, ra = b.goi(f"/ho-tro/{so['ho_tro']}/nhan", method="POST")
    if ma_s != 409:
        hong.append(f"B nhận được yêu cầu A vừa nhận: trả {ma_s}")
    elif NHAN_VIEN[0][0] not in json.dumps(ra, ensure_ascii=False):
        hong.append(f"B bị từ chối nhưng không được biết ai đang giữ: {ra}")

    # B trả lời thay A: phải bị chặn. Hai người trả lời cùng một khách hai câu
    # khác nhau là thứ hàng đợi tồn tại để tránh.
    ma_s, _ = b.goi(
        f"/ho-tro/{so['ho_tro']}/tra-loi",
        method="POST",
        than={"reply": "B trả lời thay — không được phép."},
    )
    if ma_s != 403:
        hong.append(f"B trả lời được yêu cầu do A giữ: trả {ma_s}")

    if not hong:
        _ghi("11. A nhận yêu cầu · B nhận lại → 409 nêu tên A · B trả lời thay → 403")
    return hong


def _nhan_ho_so_tuyen(a: Khach, b: Khach, so: dict) -> list[str]:
    if not so.get("ho_so_tuyen"):
        return []
    hong = []
    ma = so["ho_so_tuyen"]
    for ten, nv in (("A", a), ("B", b)):
        ma_s, ra = nv.goi("/registrations/queue?limit=200")
        if ma_s != 200:
            hong.append(f"{ten} không đọc được hàng đợi tuyển dụng: {ma_s}")
        elif ma not in _cac_ma(ra):
            hong.append(f"{ten} không thấy hồ sơ {ma} trong hàng đợi tuyển dụng")

    ma_s, ra = a.goi(f"/registrations/{ma}/accept", method="POST")
    if ma_s != 200:
        return hong + [f"A nhận hồ sơ tuyển {ma} lỗi: {ma_s} {ra}"]
    so["ma_ho_so_ung_vien"] = (ra or {}).get("profile_code")
    ma_s, ra = b.goi(f"/registrations/{ma}/accept", method="POST")
    if ma_s != 409:
        hong.append(f"B nhận được hồ sơ tuyển A vừa nhận: trả {ma_s}")

    # Sau khi nhận: hồ sơ nằm trong việc của A, không nằm trong việc của B.
    _s, cua_a = a.goi("/registrations/mine")
    _s, cua_b = b.goi("/registrations/mine")
    if ma not in _cac_ma(cua_a):
        hong.append(f"hồ sơ {ma} không nằm trong 'việc của tôi' của A")
    if ma in _cac_ma(cua_b):
        hong.append(f"hồ sơ {ma} nằm trong 'việc của tôi' của B dù A nhận")
    if not hong:
        _ghi(f"12. cả hai thấy {ma} · A nhận · B nhận lại → 409 · chỉ A có trong việc của mình")
    return hong


def _ho_so_ung_vien(a: Khach, b: Khach, so: dict) -> list[str]:
    """A — người vừa nhận khách — phải đọc được hồ sơ ứng viên và CV gốc của khách.

    Đây là yêu cầu từ bước 3 của kế hoạch kiểm thử 04/10: *"nhân viên phải nhận
    đúng CV, hồ sơ, hội thoại và đơn khách chọn"*. Phiếu tóm tắt là bản ghép; hồ
    sơ có nhãn nguồn và CV gốc mới là thứ để đối chứng khi khách nói "em không
    khai như vậy".

    B không phụ trách khách này: không được đọc cả hai.
    """
    ma_hs = so.get("ma_ho_so_ung_vien")
    if not ma_hs:
        return ["lời đáp của 'nhận hồ sơ' không mang profile_code — không lần được sang hồ sơ ứng viên"]
    hong = []
    ma_s, hs = a.goi(f"/profiles/{ma_hs}")
    if ma_s != 200:
        hong.append(f"A đã nhận khách nhưng không đọc được hồ sơ ứng viên {ma_hs}: {ma_s}")
    ma_s, tl = a.goi(f"/documents/profile/{ma_hs}")
    if ma_s != 200:
        hong.append(f"A đã nhận khách nhưng không đọc được danh sách CV của {ma_hs}: {ma_s}")
    elif so.get("co_cv"):
        ds = tl if isinstance(tl, list) else ((tl or {}).get("items") or [])
        if not ds:
            hong.append(f"khách đã gửi CV nhưng danh sách CV của {ma_hs} rỗng")
        else:
            ma_s, _ = a.goi(f"/documents/{ds[0]['code']}/text")
            if ma_s != 200:
                hong.append(f"A không mở được nội dung CV {ds[0]['code']}: {ma_s}")

    for duong in (f"/profiles/{ma_hs}", f"/documents/profile/{ma_hs}"):
        ma_s, _ = b.goi(duong)
        if ma_s == 200:
            hong.append(f"B đọc được {duong} dù A phụ trách khách này")
    if not hong:
        _ghi(f"13b. A đọc hồ sơ ứng viên {ma_hs} và CV · B → bị chặn")
    return hong


def _phieu_tom_tat(a: Khach, b: Khach, so: dict) -> list[str]:
    """A đọc được phiếu và phiếu đủ dữ liệu; B thì không đọc được."""
    if not so.get("ho_so_tuyen"):
        return []
    hong = []
    ma = so["ho_so_tuyen"]
    ma_s, phieu = a.goi(f"/registrations/{ma}/report")
    if ma_s != 200:
        return [f"A không đọc được phiếu tóm tắt của hồ sơ mình phụ trách: {ma_s} {phieu}"]
    chu = json.dumps(phieu, ensure_ascii=False)
    for nhan, can in (
        # Tên lấy từ hồ sơ của chính phiên này, không ghi cứng — xem bước 4.
        ("tên ứng viên", so.get("ten_ho_so") or "(hồ sơ không có tên)"),
        ("đơn khách chọn", so.get("don") or ""),
        ("trình độ tiếng Nhật", "N4"),
    ):
        if can and can not in chu:
            hong.append(f"phiếu tóm tắt thiếu {nhan} ({can!r})")

    ma_s, _ = b.goi(f"/registrations/{ma}/report")
    if ma_s != 403:
        hong.append(f"B đọc được phiếu của hồ sơ A phụ trách: trả {ma_s}")
    if not hong:
        _ghi(f"13. A đọc phiếu {ma} (có tên, đơn {so.get('don')}, N4) · B đọc → 403")
    return hong


def _nhat_ky_gioi_thieu(a: Khach, b: Khach, so: dict) -> list[str]:
    """Nhật ký phải giữ cả đơn BỊ LOẠI kèm lý do, và người phụ trách phải đọc được.

    Phép kiểm này không làm được từ phía công khai: `/public/matches` cố ý chỉ
    trả đơn đạt. Nhật ký là chỗ chứng minh hệ thống không âm thầm bỏ đơn nào.

    Với nhân viên thường, danh sách nhật ký **chỉ hiện hồ sơ được giao cho chính
    họ** (`api/matching.py`). Nên câu hỏi đúng không phải "có nhật ký không", mà
    là "người vừa nhận khách này có đọc được nhật ký của khách không".
    """
    ma_s, nk = a.goi(f"/recommendation-logs?session_id={so['sid']}&limit=5")
    if ma_s != 200:
        return [f"A không đọc được nhật ký giới thiệu: {ma_s}"]
    ds = nk if isinstance(nk, list) else ((nk or {}).get("items") or [])
    if not ds:
        return [
            "A đã nhận hồ sơ của khách này nhưng danh sách nhật ký giới thiệu của "
            "A không có nhật ký nào của khách — A không xem được vì sao đơn bị loại"
        ]

    so["ma_nhat_ky"] = ds[0]["code"]
    ma_s, chi = a.goi(f"/recommendation-logs/{ds[0]['code']}")
    if ma_s != 200:
        return [f"A không đọc được chi tiết nhật ký: {ma_s}"]
    cac = (chi or {}).get("items") or []
    truot = [i for i in cac if not i.get("eligible")]
    if not truot:
        return ["nhật ký không giữ đơn bị loại — không có gì chứng minh bộ lọc chạy"]
    if not any(r.get("result") == "KHONG_DAT" for i in truot for r in i.get("hard_rows") or []):
        return ["đơn bị loại trong nhật ký không ghi lý do nào"]

    # B không phụ trách khách này: không được đọc nhật ký của họ.
    ma_s, _ = b.goi(f"/recommendation-logs/{ds[0]['code']}")
    if ma_s == 200:
        return [f"B đọc được nhật ký giới thiệu của khách do A phụ trách"]
    _ghi(f"14. A đọc nhật ký: {len(cac)} đơn đã xét, {len(truot)} bị loại kèm lý do · B → {ma_s}")
    return []


def _khong_co_quyen_quan_ly(a: Khach, so: dict) -> list[str]:
    """Kiểm ngược: tài khoản thử đúng là nhân viên thường, không phải quản lý.

    Chuyển người phụ trách là việc của quản lý (`ensure_can_assign`). A làm được
    thì hoặc A không phải consultant, hoặc chốt phân quyền đã hỏng — và cả hai
    trường hợp đều làm mọi phép đo phía trên mất nghĩa.
    """
    if not so.get("ho_so_tuyen"):
        return []
    ma_s, _ = a.goi(
        f"/registrations/{so['ho_so_tuyen']}/handover",
        method="POST",
        than={"assigned_to": NHAN_VIEN[1][0], "note": "E2E kiểm phân quyền"},
    )
    if ma_s == 422:
        # Thân yêu cầu sai hình dạng thì máy chủ từ chối TRƯỚC khi tới chốt
        # phân quyền — một 422 ở đây không nói gì về quyền cả.
        return ["bộ đo gửi sai thân yêu cầu handover (422) — phép kiểm phân quyền không chạy"]
    if ma_s != 403:
        return [f"nhân viên thường chuyển được người phụ trách: trả {ma_s}"]
    _ghi("15. A thử chuyển hồ sơ cho B → 403 (việc của quản lý)")
    return []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8020")
    ap.add_argument("--hoi", action="store_true", help="hỏi trợ lý một câu thật")
    ap.add_argument(
        "--khai-tay",
        action="store_true",
        help="bỏ bước đọc CV, khai hồ sơ tay từ đáp án — không gọi mô hình lượt nào",
    )
    ap.add_argument(
        "--giu-tai-khoan",
        action="store_true",
        help="không xóa tài khoản nhân viên tạm khi xong",
    )
    args = ap.parse_args()

    ma_s, _ = Khach(args.url).goi("/health")
    if ma_s != 200:
        print(f"Backend không trả lời ở {args.url} — bỏ qua.")
        return 2

    print(f"Hành trình đầy đủ qua HTTP · {args.url}")
    print(f"CV mẫu: {CV_FILE} (tên và số liệu đều là giả)")
    them = " + 1 lượt hỏi trợ lý" if args.hoi else ""
    if args.khai_tay:
        print("Chế độ KHAI TAY: bỏ bước đọc CV và lượt mở đầu sau CV — hai bước đó KHÔNG được đo")
        print(f"Gọi mô hình: {'1 lượt hỏi trợ lý' if args.hoi else 'không lượt nào'}")
    else:
        print(f"Gọi mô hình: 1 lượt cho bước đọc CV{them}")
    print()

    tu_tao = asyncio.run(_tao_nhan_vien())
    print(f"Tài khoản tạm (2 consultant + 1 manager): vừa tạo {len(tu_tao)}, dùng lại {len(NHAN_VIEN) + 1 - len(tu_tao)}")
    print()
    hong: list[str] = []
    so: dict = {}
    try:
        hong, so = chay(args.url, hoi=args.hoi, khai_tay=args.khai_tay)
        if so.get("ho_tro") and not so.get("khong_do_duoc"):
            hong += phan_nhan_vien(args.url, so)
    except Exception as exc:  # noqa: BLE001
        # Một bước nổ không được làm mất bản tổng kết. Thiếu nó thì mọi chỗ hỏng
        # đã tìm ra trước đó biến mất khỏi màn hình, và lần chạy coi như vô ích.
        import traceback

        traceback.print_exc()
        hong.append(f"bộ đo nổ: {type(exc).__name__}: {exc}")
    finally:
        if tu_tao and not args.giu_tai_khoan:
            n = asyncio.run(_xoa_nhan_vien(tu_tao))
            print(f"\nĐã xóa {n} tài khoản nhân viên tạm.")

    print()
    print("=" * 72)
    for h in hong:
        print(f"  ! {h}")
    if so.get("khong_do_duoc"):
        print(f"HÀNH TRÌNH: KHÔNG ĐO ĐƯỢC — {so['khong_do_duoc']}")
        return KHONG_DO_DUOC
    for k in so.get("khong_do") or ():
        print(f"  ? KHÔNG ĐO ĐƯỢC — {k}")
    print(f"HÀNH TRÌNH: {len(hong)} chỗ hỏng")
    return ket_luan(hong=hong, khong_do=so.get("khong_do") or [])


def ket_luan(*, hong: list[str], khong_do: list[str]) -> int:
    """Mã thoát của hành trình — `nghiem_thu_chot` quyết định theo nó.

    Bản trước in các mục "KHÔNG ĐO ĐƯỢC" (dấu `?`) rồi vẫn thoát 0. Tức là một lượt
    mà lời tư vấn không đến từ mô hình, hay phép kiểm chống trùng bị bộ giới hạn
    chặn trước, vẫn được bộ chốt tính là ĐẠT. Cùng loại lỗi với `nghiem_thu_agent`
    luôn trả 0 mà chủ đồ án bắt ngày 06/10.

    Có chỗ hỏng → 1 (kết luận chắc chắn, thắng mọi thứ khác); có mục chưa đo được
    → `KHONG_DO_DUOC`; còn lại → 0.
    """
    if hong:
        return 1
    if khong_do:
        return KHONG_DO_DUOC
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
