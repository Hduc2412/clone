"""Nghiệm thu xuyên suốt: năm hồ sơ đi hết hành trình, trên dữ liệu đơn thật.

Chạy:  venv/Scripts/python.exe -m scripts.nghiem_thu_xuyen_suot

Cờ:
  --tat-ai       chạy với `ADVISOR_ENABLED=false`, đo nhánh "AI hết hạn mức"

## Khác gì những bộ đo đã có

| Bộ | Đo gì |
|---|---|
| `nghiem_thu_doc_cv` | Một bước: máy đọc CV có đúng không |
| `nghiem_thu_tu_van` | Một lượt: bot có bịa không |
| `nghiem_thu_agent` | Một lượt: khối có cấu trúc có đúng hình không |
| **bộ này** | **Cả chuỗi**, năm hồ sơ khác nhau, từ hồ sơ tới kết quả đối chiếu và lời tư vấn |

Một bước đúng mà cả chuỗi sai thì vẫn là sai. Ví dụ thật đã gặp: ô điểm được ẩn
đúng ở bước hiển thị, nhưng câu giải thích ngay bên dưới vẫn nói ra con số vừa
ẩn — hai bước đều "đúng" theo bộ đo của riêng nó.

## Không gọi mô hình

Mọi thứ ở đây dựng bằng quy tắc: bộ đối chiếu, câu giải thích ghép sẵn, lượt mở
đầu của Agent, bản bàn giao. Nhờ vậy bộ này **chạy được khi hết hạn mức** và cho
cùng kết quả mỗi lần — đúng hai tính chất mà một bộ nghiệm thu cần.

Phần chất lượng lời mô hình viết nằm ở `nghiem_thu_agent`, chạy riêng.

## Vì sao cờ `--tat-ai` là một ca, không phải một chế độ

Hết hạn mức là **trạng thái vận hành bình thường** của gói miễn phí: 20 lượt mỗi
ngày, dùng chung giữa đo chất lượng và chạy thật. Nên "hệ thống còn gì khi AI im"
là một câu hỏi nghiệm thu, không phải một tình huống ngoại lệ.
"""
import sys

import app  # noqa: F401  — đặt stdout về UTF-8
from app.advisor import phrasing
from app.agent import ban_giao, mo_dau, state
from app.consultation import advice as advice_builder
from app.core.config import settings
from app.core.timeutil import local_today
from app.db import candidate_profiles as profiles
from app.matching import engine, explain
from app.matching.weights import load_weights
from scripts.seed_data.courses_seed import COURSES
from scripts.seed_job_orders import build_documents


WEIGHTS = load_weights()
AS_OF = local_today()


def pool():
    return [d for d in build_documents() if d.get("published")]


def ho_so(**truong):
    """Hồ sơ đã xác nhận, hình dạng y như bản trong database."""
    return {
        "code": "UV-NT",
        "session_id": "nt",
        "status": profiles.STATUS_CONFIRMED,
        "version": 1,
        "fields": {
            k: profiles.cell(v, "user_confirmed")
            for k, v in truong.items()
            if k not in _NGUYEN_VONG
        },
        "preferences": {
            k: profiles.cell(v, "user_confirmed")
            for k, v in truong.items()
            if k in _NGUYEN_VONG
        },
    }


_NGUYEN_VONG = frozenset(
    {
        "desired_prefecture",
        "desired_region_group",
        "desired_employer_type",
        "salary_expectation_jpy",
        "budget_vnd",
    }
)


class Ca:
    def __init__(self, ma: str, mo_ta: str, truong: dict, *, kiem) -> None:
        self.ma = ma
        self.mo_ta = mo_ta
        self.truong = truong
        self.kiem = kiem


def _co_don_dat(kq) -> list:
    return [i for i in kq.items if i.eligible]


# --- Năm ca ---


def _kiem_n4_phu_hop(kq, hs) -> list[str]:
    """N4, cao đẳng, nêu nguyện vọng rõ → phải có đơn đạt VÀ xếp hạng được."""
    hong = []
    dat = _co_don_dat(kq)
    if not dat:
        hong.append("không có đơn nào đạt — hồ sơ này lẽ ra nộp được nhiều đơn")
        return hong
    nhat = next((i for i in dat if i.rank == 1), dat[0])
    if not engine.xep_hang_duoc(nhat.soft_rows):
        hong.append("đã nêu nguyện vọng mà vẫn không xếp hạng được")
    if nhat.score == 0:
        hong.append("đơn hạng 1 có 0 điểm dù đã nêu nguyện vọng")
    cau = explain.render_template_text(nhat)
    if "Xếp hạng" not in cau:
        hong.append("câu giải thích không nói thứ hạng dù xếp hạng được")
    return hong


def _kiem_chua_hoc_tieng(kq, hs) -> list[str]:
    """Chưa học tiếng Nhật → **không đơn nào** nộp được, và phải có lối đi tiếp.

    ## Vì sao kỳ vọng ở đây là "không đơn nào", không phải "còn đơn N5"

    Bản đầu của ca này kỳ vọng vẫn còn đơn đạt, lý luận rằng *"đơn thực tập sinh
    chỉ cần N5"*. Sai ở một bậc: `chua_hoc` nằm **dưới** N5, nên đơn N5 cũng loại.
    Đo lại trên 18 đơn đang mở thì cả 18 đều đòi từ N5 lên (N5 5 đơn, N4 7, N3 6).

    Vậy con số 0 là **đúng nghiệp vụ**, không phải lỗi: chưa học tiếng thì chưa
    nộp được gì, phải học trước. Chính vì thế nhánh tư vấn học tồn tại.

    Cái phải kiểm là **hệ thống nói gì tiếp theo**:

    1. Lý do loại phải là tiếng Nhật, không phải một tiêu chí khác.
    2. Phải có ít nhất một đơn mà tiếng Nhật là **chướng ngại duy nhất** — đó
       chính là đơn đáng đem ra tư vấn học, vì học xong là nộp được thật.
    3. Với đúng đơn đó, lộ trình học phải dựng được từ danh mục khóa thật.
    """
    hong = []
    if _co_don_dat(kq):
        hong.append("chưa học tiếng mà vẫn có đơn đạt — bộ lọc tiếng Nhật hỏng")

    truot = [i for i in kq.items if not i.eligible]
    vuong = {
        i.code: tuple(
            r.key for r in i.hard_rows if r.result == engine.KHONG_DAT
        )
        for i in truot
    }
    if not any("japanese" in v for v in vuong.values()):
        hong.append("không đơn nào bị loại vì tiếng Nhật — bộ lọc cứng không chạy?")

    # Đơn mà tiếng Nhật là chướng ngại DUY NHẤT. Học xong là nộp được thật, nên
    # đây là đơn đáng đem ra tư vấn học.
    chi_vuong_tieng = [ma for ma, v in vuong.items() if v == ("japanese",)]
    if not chi_vuong_tieng:
        hong.append(
            "không đơn nào chỉ vướng tiếng Nhật — không có gì để tư vấn học"
        )
        return hong

    don = next(i for i in truot if i.code == chi_vuong_tieng[0])
    kq_advice = advice_builder.build(
        don,
        # `MatchItem` không mang `requirements` — tra lại từ danh mục đơn, đúng
        # như `api/consultation_room.py` làm.
        required_japanese=(
            next(d for d in pool() if d["code"] == don.code).get("requirements") or {}
        ).get("japanese_required"),
        profile_level="chua_hoc",
        courses=COURSES,
        profile_confirmed=True,
    )
    if kq_advice.learning is None:
        hong.append(
            f"{don.code} chỉ vướng tiếng mà không dựng được lộ trình: "
            f"{kq_advice.learning_note or 'không nói lý do'}"
        )
    else:
        # Lộ trình nói tiền thì **bắt buộc** nói cả tổng chi phí chương trình.
        # 35 triệu học phí là một chặng trong tổng 90 triệu; nói trơ trọi là để
        # khách hiểu sai số tiền phải chuẩn bị — xem `consultation/advice.py`.
        khoi = advice_builder.render_block(kq_advice)
        if "35" in khoi and "90" not in khoi:
            hong.append("khối tư vấn nói học phí mà không nói tổng chi phí chương trình")
    return hong


def _kiem_thieu_thong_tin(kq, hs) -> list[str]:
    """Hồ sơ khuyết → KHÔNG được loại đơn, và KHÔNG được nói thứ hạng."""
    hong = []
    dat = _co_don_dat(kq)
    if not dat:
        hong.append("thiếu thông tin mà mất hết đơn — 'chưa rõ' đang bị coi là 'không đạt'")
        return hong

    # Phải có dòng CHƯA RÕ, và đơn vẫn đạt.
    co_chua_ro = any(
        any(r.result == engine.CHUA_RO for r in i.hard_rows) for i in dat
    )
    if not co_chua_ro:
        hong.append("không dòng nào CHƯA RÕ dù hồ sơ khuyết")

    nhat = next((i for i in dat if i.rank == 1), dat[0])
    if engine.xep_hang_duoc(nhat.soft_rows):
        hong.append("chưa nêu nguyện vọng nào mà vẫn báo xếp hạng được")
    cau = explain.render_template_text(nhat)
    if "Xếp hạng" in cau or "/100" in cau:
        hong.append(f"câu giải thích vẫn nói thứ hạng: {cau[-90:]!r}")
    khoi = explain.render_block(nhat)
    if "tổng " in khoi:
        hong.append("khối ngữ cảnh mô hình đọc vẫn mang điểm")
    if not kq.missing_info:
        hong.append("không sinh câu hỏi nào cho dữ liệu còn thiếu")
    return hong


def _kiem_qua_tuoi(kq, hs) -> list[str]:
    """Quá tuổi mọi đơn → phải nói rõ vướng tuổi, KHÔNG nói về cả chương trình."""
    hong = []
    truot = [i for i in kq.items if not i.eligible]
    if not truot:
        hong.append("38 tuổi mà không đơn nào loại vì tuổi")
        return hong
    co_tuoi = any(
        any(r.key == "age" and r.result == engine.KHONG_DAT for r in i.hard_rows)
        for i in truot
    )
    if not co_tuoi:
        hong.append("không đơn nào ghi lý do loại là độ tuổi")
    # Chốt phạm vi: câu giải thích nói về ĐƠN, không nói về CHƯƠNG TRÌNH.
    for i in truot[:5]:
        cau = explain.render_template_text(i)
        if "chương trình" in cau.lower():
            hong.append(f"{i.code}: câu giải thích nới ra cả chương trình")
    return hong


def _kiem_doi_don(kq, hs) -> list[str]:
    """Đổi đơn: kết quả của mỗi đơn độc lập, và tất định."""
    hong = []
    dat = _co_don_dat(kq)
    if len(dat) < 2:
        hong.append("cần ít nhất hai đơn đạt để kiểm việc đổi đơn")
        return hong

    # Đối chiếu riêng từng đơn phải cho cùng kết quả như khi đối chiếu cả danh mục.
    for i in dat[:3]:
        rieng = engine.match_orders(
            [d for d in pool() if d.get("code") == i.code],
            engine.build_facts(hs, AS_OF),
            weights=WEIGHTS,
            as_of=AS_OF,
        )
        mot = rieng.items[0]
        if mot.eligible != i.eligible or mot.score != i.score:
            hong.append(
                f"{i.code}: đối chiếu riêng cho kết quả khác "
                f"({mot.eligible}/{mot.score} vs {i.eligible}/{i.score})"
            )
    # Tất định: xáo trộn danh mục vẫn ra cùng thứ tự.
    lan_2 = engine.match_orders(
        list(reversed(pool())), engine.build_facts(hs, AS_OF), weights=WEIGHTS, as_of=AS_OF
    )
    if [i.code for i in lan_2.items] != [i.code for i in kq.items]:
        hong.append("xáo trộn danh mục cho ra thứ tự khác — mất tính tất định")
    return hong


BO_CA = (
    Ca(
        "N4-PHU-HOP",
        "N4, cao đẳng, 27 tuổi, muốn Tokyo viện dưỡng lão",
        {
            "full_name": "Ca Một",
            "japanese_level": "N4",
            "education_level": "cao_dang",
            "birth_year": AS_OF.year - 27,
            "gender": "nu",
            "experience_years": 3,
            "care_experience": True,
            "desired_prefecture": "Tokyo",
            "desired_region_group": "kanto",
            "desired_employer_type": "vien_duong_lao",
            "salary_expectation_jpy": 190_000,
            "budget_vnd": 90_000_000,
        },
        kiem=_kiem_n4_phu_hop,
    ),
    Ca(
        "CHUA-HOC-TIENG",
        "Chưa học tiếng Nhật, trung cấp, 19 tuổi",
        {
            "full_name": "Ca Hai",
            "japanese_level": "chua_hoc",
            "education_level": "trung_cap",
            "birth_year": AS_OF.year - 19,
            "gender": "nu",
            "care_experience": False,
            "desired_employer_type": "vien_duong_lao",
        },
        kiem=_kiem_chua_hoc_tieng,
    ),
    Ca(
        "THIEU-THONG-TIN",
        "Chỉ có họ tên và N4 — không năm sinh, không nguyện vọng",
        {"full_name": "Ca Ba", "japanese_level": "N4"},
        kiem=_kiem_thieu_thong_tin,
    ),
    Ca(
        "QUA-TUOI",
        "38 tuổi, N4, cao đẳng — quá tuổi phần lớn đơn",
        {
            "full_name": "Ca Bốn",
            "japanese_level": "N4",
            "education_level": "cao_dang",
            "birth_year": AS_OF.year - 38,
            "gender": "nam",
            "desired_prefecture": "Tokyo",
        },
        kiem=_kiem_qua_tuoi,
    ),
    Ca(
        "DOI-DON",
        "N4 đủ điều kiện nhiều đơn — kiểm đổi đơn và tính tất định",
        {
            "full_name": "Ca Năm",
            "japanese_level": "N4",
            "education_level": "cao_dang",
            "birth_year": AS_OF.year - 25,
            "gender": "nu",
            "experience_years": 2,
            "care_experience": True,
            "desired_prefecture": "Tokyo",
            "desired_region_group": "kanto",
        },
        kiem=_kiem_doi_don,
    ),
)


def chay_mot_ca(ca: "Ca") -> tuple[list[str], dict[str, str]]:
    """Chạy một ca, trả `(chỗ hỏng, hiện vật)`.

    "Hiện vật" là những đoạn chữ khách và nhân viên thật sự đọc. Trả chúng ra để
    chạy lại được với engine tắt rồi **so từng ký tự** — xem `so_hai_che_do`.
    """
    hs = ho_so(**ca.truong)
    kq = engine.match_orders(
        pool(), engine.build_facts(hs, AS_OF), weights=WEIGHTS, as_of=AS_OF
    )
    hong = ca.kiem(kq, hs)

    log = {
        "total_considered": kq.total_considered,
        "eligible_count": len(_co_don_dat(kq)),
        "items": [i.as_dict() for i in kq.items],
    }
    hien_vat: dict[str, str] = {}

    # Lượt mở đầu và bản bàn giao phải dựng được ở MỌI ca, kể cả khi engine tắt
    # — đó là điều khiến hệ thống còn dùng được lúc AI im.
    try:
        cau_mo_dau = mo_dau.sau_matching(log, profile=hs)
        if not cau_mo_dau.strip():
            hong.append("lượt mở đầu rỗng")
    except Exception as exc:  # noqa: BLE001
        hong.append(f"lượt mở đầu nổ: {type(exc).__name__}: {exc}")
        cau_mo_dau = ""
    hien_vat["mo_dau"] = cau_mo_dau

    try:
        tt = state.suy_ra(profile=hs, log=log)
        ban = ban_giao.dung(profile=hs, trang_thai=tt, log=log)
        if "VIỆC NÊN LÀM TIẾP" not in ban:
            hong.append("bản bàn giao thiếu phần việc nên làm tiếp")
        hien_vat["ban_giao"] = ban
    except Exception as exc:  # noqa: BLE001
        hong.append(f"bản bàn giao nổ: {type(exc).__name__}: {exc}")

    # Lời giải thích của đơn hạng nhất — đoạn khách đọc ngay dưới ô điểm.
    dat = _co_don_dat(kq)
    if dat:
        nhat = next((i for i in dat if i.rank == 1), dat[0])
        hien_vat["giai_thich"] = explain.render_template_text(nhat)
        hien_vat["khoi_ai"] = explain.render_block(nhat)

    # Mọi lý do "nhờ ..." phải truy về được một dòng mềm CÓ THẬT.
    #
    # Đây là chỗ lỗi 05/10 ẩn mình: dòng chi phí được 5 điểm khi *chưa rõ*, nên
    # câu mở đầu khen "nhờ chi phí" một hồ sơ chưa nêu ngân sách. Đo từng bước
    # thì cả hai bước đều đúng theo luật của riêng nó — chỉ cả chuỗi mới thấy sai.
    if "nhờ " in cau_mo_dau:
        ly_do = cau_mo_dau.split("nhờ ", 1)[1].split(".")[0]
        nhan_that = {
            r.label.lower()
            for i in dat
            for r in i.soft_rows
            if r.points > 0 and r.outcome not in explain.NON_REASONS
        }
        for cum in ly_do.split(" và "):
            if cum.strip() and cum.strip() not in nhan_that:
                hong.append(f"lý do {cum.strip()!r} không truy về dòng mềm nào có thật")

    # Không câu nào được chứa cụm hứa hẹn.
    thap = cau_mo_dau.lower()
    for cum in phrasing.CUM_TU_CAM + phrasing.CUM_TU_CAM_KET:
        if cum in thap:
            hong.append(f"lượt mở đầu chứa cụm cấm {cum!r}")
    if phrasing._HUA_CHAC.search(cau_mo_dau):
        hong.append("lượt mở đầu hứa chắc kết quả")

    return hong, hien_vat


def _chay_het(*, im: bool = False) -> tuple[int, dict[str, dict[str, str]]]:
    tong_hong = 0
    moi_hien_vat: dict[str, dict[str, str]] = {}
    for ca in BO_CA:
        hong, hien_vat = chay_mot_ca(ca)
        moi_hien_vat[ca.ma] = hien_vat
        tong_hong += len(hong)
        if im:
            continue
        print(f"[{'ĐẠT ' if not hong else 'HỎNG'}] {ca.ma} — {ca.mo_ta}")
        print(f"   trợ lý mở đầu: {hien_vat.get('mo_dau', '')[:150]}…")
        for h in hong:
            print(f"   ! {h}")
        print()
    return tong_hong, moi_hien_vat


def so_hai_che_do() -> list[str]:
    """Engine tư vấn bật và tắt phải cho **cùng từng ký tự**.

    Đây là câu trả lời đo được cho "hết hạn mức Gemini thì sao". Nếu một đoạn
    chữ nào đổi khi tắt engine thì đoạn ấy phụ thuộc mô hình, và ngày hết hạn
    mức nó sẽ biến mất khỏi màn hình khách hoặc khỏi bản bàn giao.

    Hạn mức gói miễn phí là 20 lượt mỗi ngày trên mỗi dự án và mỗi model, dùng
    chung giữa đo chất lượng và chạy thật — nên hết hạn mức là trạng thái vận
    hành bình thường, không phải sự cố.
    """
    goc = settings.advisor_enabled
    try:
        settings.advisor_enabled = True
        _, bat = _chay_het(im=True)
        settings.advisor_enabled = False
        _, tat = _chay_het(im=True)
    finally:
        settings.advisor_enabled = goc

    lech = []
    for ma in bat:
        for khoa in bat[ma]:
            if bat[ma][khoa] != tat.get(ma, {}).get(khoa):
                lech.append(f"{ma}/{khoa} đổi khi tắt engine tư vấn")
    return lech


def main() -> int:
    chi_tat_ai = "--tat-ai" in sys.argv
    if chi_tat_ai:
        settings.advisor_enabled = False

    print(
        f"Nghiệm thu xuyên suốt · {len(pool())} đơn công khai · ngày {AS_OF.isoformat()}"
    )
    print(f"Engine tư vấn: {'TẮT (đo nhánh hết hạn mức)' if chi_tat_ai else 'bật'}")
    print("Không gọi mô hình: mọi thứ ở đây dựng bằng quy tắc.")
    print()

    tong_hong, _ = _chay_het()

    if not chi_tat_ai:
        print("--- Đối chứng: bật và tắt engine tư vấn phải cho cùng từng ký tự")
        lech = so_hai_che_do()
        for l in lech:
            print(f"   ! {l}")
        if not lech:
            print("   không đoạn chữ nào đổi — hết hạn mức vẫn đủ chữ để đi tiếp")
        tong_hong += len(lech)
        print()

    print("=" * 72)
    print(f"TỔNG: {len(BO_CA)} ca · {tong_hong} chỗ hỏng")
    return 1 if tong_hong else 0


if __name__ == "__main__":
    raise SystemExit(main())
