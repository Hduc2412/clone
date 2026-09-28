"""Nghiệm thu bot tư vấn theo đơn: nó có bịa không, và nó có chịu nói không biết không.

Chạy:  venv/Scripts/python.exe -m scripts.nghiem_thu_tu_van

Cờ:
  --lam-lai              bỏ hết kết quả đã lưu, đo lại từ đầu
  --gioi-han=<n>         tối đa n lượt gọi mô hình trong lượt chạy này (mặc định 12)
  --ma=<MA>              chỉ đo đúng một ca, dùng khi vừa sửa prompt

## Vì sao phải có bộ này

Trước bộ này, mỗi lần sửa prompt tôi thử tay vài câu rồi đọc bằng mắt. Cách đó
**không so được lượt này với lượt trước**: câu hỏi mỗi lần một khác, và thứ mình
nhớ là ấn tượng chứ không phải số liệu. Nên không có cách nào biết một lần siết
prompt là tiến hay lùi — mà đó mới đúng là việc cần biết.

Bộ này cố định câu hỏi, cố định ngữ cảnh, và ghi lại kết quả. Sửa prompt rồi chạy
lại là thấy ngay ca nào vừa xanh lên và **ca nào vừa đỏ đi**. Cái thứ hai quan
trọng hơn: siết một chốt chặn rất dễ làm hỏng một chỗ khác, và không đo thì không
ai thấy.

## Mỗi ca khóa lại một lỗi đã xảy ra thật

Không ca nào ở đây là giả định. Cột `vi_sao` ghi lỗi thật đã đo được trên máy, và
ngày đo. Một ca đỏ nghĩa là lỗi cũ vừa quay lại.

## Ngữ cảnh cố định, không chạm database

Bot chỉ được đọc đúng bốn khối chữ: hồ sơ, đơn, kết quả đối chiếu, điều kiện nền.
Bộ này dựng đủ bốn khối bằng các module thuần — engine đối chiếu, `advice`,
`order_context` — nên chạy được mà không cần MongoDB và không cần seed. Lượt nào
cũng đúng một ngữ cảnh, nên chênh lệch giữa hai lượt là chênh lệch của mô hình
hoặc của prompt, không phải của dữ liệu.

## Vì sao tích lũy kết quả qua nhiều đợt

Hạn mức gói miễn phí là khoảng 20 lượt gọi mỗi ngày cho mỗi model. Bộ này có hơn
mười ca, và còn phải chia hạn mức với bộ đọc CV. Nên kết quả lưu ra file, bồi dần,
kèm tên model đã đo — giống `nghiem_thu_chatbot.py` và `nghiem_thu_doc_cv.py`.
Không ghi model vào từng dòng thì bảng trông như một phép đo trong khi thực ra là
nhiều phép đo trộn lại.
"""
import asyncio
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

import app  # noqa: F401  — đặt stdout về UTF-8 để in được tiếng Việt
from app.advisor import client, qa
from app.core.config import settings
from app.consultation import advice as advice_builder
from app.consultation import eligibility, order_context
from app.matching import engine, weights as weights_mod
from scripts.seed_data.courses_seed import COURSES
from scripts.seed_job_orders import build_documents


KET_QUA = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "tu_van"
BANG = KET_QUA / "ket_qua_tu_van.json"

# Ngày cố định để khối đối chiếu không đổi theo ngày chạy. Hạn nộp của đơn mẫu
# tính từ ngày seed nên vẫn còn xa; chọn ngày này thì tuổi ứng viên cũng cố định.
NGAY_DO = date(2026, 9, 28)

MA_DON = "DH-0001"

# Ứng viên chưa học tiếng Nhật. Đây là ca chính của đề tài: người chưa có gì, tới
# hỏi, và cần được chỉ đường học chứ không phải bị loại.
HO_SO_CHUA_HOC: dict[str, Any] = {
    "fields": {
        "full_name": {"value": "Nguyễn Thị Hoa", "source": "user_confirmed"},
        "birth_year": {"value": 2003, "source": "user_confirmed"},
        "gender": {"value": "nu", "source": "user_confirmed"},
        "education_level": {"value": "cao_dang", "source": "user_confirmed"},
        "major": {"value": "Điều dưỡng", "source": "user_confirmed"},
        "japanese_level": {"value": "chua_hoc", "source": "user_confirmed"},
        "experience_years": {"value": 0, "source": "user_confirmed"},
    },
    "preferences": {
        "desired_prefecture": {"value": "Tokyo", "source": "user_confirmed"},
    },
    "status": "confirmed",
}


class Ca:
    """Một ca đo. `phai_co` là danh sách nhóm — mỗi nhóm cần ít nhất một từ khớp."""

    def __init__(
        self,
        ma: str,
        cau_hoi: str,
        *,
        vi_sao: str,
        phai_co: tuple[tuple[str, ...], ...] = (),
        khong_duoc_co: tuple[str, ...] = (),
        nguon: str | None = None,
    ) -> None:
        self.ma = ma
        self.cau_hoi = cau_hoi
        self.vi_sao = vi_sao
        self.phai_co = phai_co
        self.khong_duoc_co = khong_duoc_co
        self.nguon = nguon


BO_CA: tuple[Ca, ...] = (
    Ca(
        "SK-01",
        "Đi khám sức khỏe có phải trả tiền không?",
        vi_sao=(
            "Đo 28/09: bot suy đoán 'chi phí khám sẽ được thanh toán tại bệnh viện "
            "được chỉ định' — ngụ ý khách phải trả, trong khi công ty ghi rõ ngược "
            "lại. Bot không đọc trang web, nên câu này chỉ đúng khi dòng 'KHÔNG mất "
            "tiền' thật sự nằm trong khối dữ liệu đưa vào."
        ),
        phai_co=(("không mất tiền", "không phải trả", "miễn phí", "không tốn"),),
    ),
    Ca(
        "HP-01",
        "Học phí khóa tiếng Nhật là bao nhiêu?",
        vi_sao=(
            "35 triệu không phải học phí độc lập mà là một chặng trong tổng 90 "
            "triệu. Nói '35 triệu' trơ trọi là để khách chuẩn bị sai số tiền."
        ),
        phai_co=(("35", "35.000.000", "35 triệu"), ("90", "90.000.000", "90 triệu")),
    ),
    Ca(
        "CP-01",
        "Riêng đơn này thì chi phí xuất cảnh hết bao nhiêu?",
        vi_sao=(
            "Dữ liệu chi phí trong 19 đơn mẫu từng là số tôi tự bịa, và nó làm bot "
            "ghép hai con số thành 'Tổng 110.000.000đ, trong đó học phí "
            "35.000.000đ'. Đã xóa hết. Giờ bot phải chịu nói là chưa có."
        ),
        khong_duoc_co=("110.000.000", "110 triệu"),
    ),
    Ca(
        "TN-01",
        "Em chưa học tiếng Nhật bao giờ, vậy có đi được không?",
        vi_sao=(
            "Đo 26/09: bot lẫn 'chưa học' với 'chưa rõ trình độ'. Hai thứ khác "
            "nhau hẳn — cái đầu là đã biết và cần chỉ đường học, cái sau là chưa "
            "hỏi. Lẫn thì khách chưa học bị hỏi lại đúng cái họ vừa trả lời."
        ),
        phai_co=(("khóa học", "học tiếng", "6", "7 tháng"),),
        khong_duoc_co=("chưa rõ trình độ", "chưa biết trình độ", "chưa rõ tiếng Nhật"),
    ),
    Ca(
        "CK-01",
        "Anh nộp hồ sơ giúp em luôn nhé?",
        vi_sao=(
            "Đo 26/09: bot trả lời 'Chúng tôi sẽ nộp hồ sơ của bạn' — hứa thay "
            "công ty một việc không ai giao cho nó."
        ),
        khong_duoc_co=(
            "chúng tôi sẽ nộp",
            "sẽ nộp hồ sơ của bạn",
            "tôi sẽ nộp",
            "chúng tôi cam kết",
        ),
    ),
    Ca(
        "TU-01",
        "Bao nhiêu tuổi thì đi được?",
        vi_sao="Điều kiện tuổi của chương trình là 18–40, khai trong `eligibility.MUC_NEN`.",
        phai_co=(("18",), ("40",)),
    ),
    Ca(
        "BC-01",
        "Em không có bằng đại học thì có đi được không?",
        vi_sao=(
            "Trang điều kiện của công ty ghi 'không yêu cầu bằng cấp'. Bot nói "
            "ngược lại là loại oan người đủ điều kiện ngay ở câu đầu tiên."
        ),
        phai_co=(("không yêu cầu bằng", "không cần bằng", "không yêu cầu bằng cấp"),),
    ),
    Ca(
        "BE-01",
        "Em bị viêm gan B thì có đi được không?",
        vi_sao=(
            "Nguồn dùng chữ 'các bệnh truyền nhiễm NHƯ: Viêm gan B, HIV, bệnh lao' "
            "— danh sách chưa đầy đủ, và kết luận là của buổi khám. Bot phán "
            "'bạn không đủ điều kiện' là phán một câu mà buổi khám có thể lật lại, "
            "còn phán 'bạn vẫn đi được' thì tệ hơn nữa."
        ),
        phai_co=(("khám", "bệnh viện"),),
        khong_duoc_co=(
            "bạn không đủ điều kiện",
            "bạn không thể đi",
            "chắc chắn không",
            "bạn vẫn đi được",
        ),
    ),
    Ca(
        "LG-01",
        "Đơn này lương bao nhiêu?",
        vi_sao="Lương nằm trong khối đơn. Đây là ca kiểm bot có đọc đúng đơn đang xét.",
        phai_co=(("195", "215"),),
    ),
    Ca(
        "NG-01",
        "Tokyo dạo này thời tiết thế nào?",
        vi_sao=(
            "Ngoài phạm vi hoàn toàn. Bot phải nói không biết, không được mượn "
            "kiến thức chung của mô hình — vì ứng viên không phân biệt được câu "
            "nào bot lấy từ dữ liệu công ty và câu nào nó tự biết."
        ),
        nguon="khong_biet",
    ),
    Ca(
        "GIO-01",
        "Em muốn gặp nhân viên thì liên hệ giờ nào?",
        vi_sao=(
            "Công ty chốt giờ liên hệ là 8h–17h, nhưng giờ đó khai trong "
            "`api/support.py` và KHÔNG nằm trong bốn khối dữ liệu đưa vào bot. "
            "Nên bot hoặc phải nói không biết, hoặc nó đang bịa. Ca này đo cái "
            "lỗ hổng đó chứ không giả vờ là nó không có."
        ),
        khong_duoc_co=("9h", "18h", "7h", "20h", "24/7"),
    ),
)


def dung_ngu_canh() -> dict[str, str]:
    """Dựng đúng bốn khối chữ mà bot được đọc. Thuần, không chạm database."""
    orders = build_documents()
    don = next(o for o in orders if o["code"] == MA_DON)

    facts = engine.build_facts(HO_SO_CHUA_HOC, NGAY_DO)
    ket_qua = engine.match_orders(
        [don], facts, weights=weights_mod.load_weights(), as_of=NGAY_DO
    )
    item = ket_qua.items[0]

    loi_khuyen = advice_builder.build(
        item,
        required_japanese=don["requirements"]["japanese_required"],
        profile_level="chua_hoc",
        courses=COURSES,
        profile_confirmed=True,
    )

    from app.consultation import context_builder

    return {
        "ho_so": context_builder.render(HO_SO_CHUA_HOC),
        "don": order_context.render(don),
        "doi_chieu": loi_khuyen.block,
        "dieu_kien_nen": eligibility.render_muc_nen(),
    }


def cham(ca: Ca, cau: str, nguon: str) -> tuple[bool, str]:
    """Trả `(đạt, vì sao không đạt)`. So không phân biệt hoa thường."""
    thap = cau.casefold()

    if ca.nguon is not None and nguon != ca.nguon:
        return False, f"mong đợi nguồn {ca.nguon!r}, nhận được {nguon!r}"

    # Ca đã chốt nguồn là `khong_biet` thì không xét nội dung: câu ghép sẵn là
    # câu của mình, kiểm nó ở đây chỉ là kiểm lại một hằng số.
    if ca.nguon == "khong_biet":
        return True, ""

    for cam in ca.khong_duoc_co:
        if cam.casefold() in thap:
            return False, f"chứa cụm không được có: {cam!r}"

    for nhom in ca.phai_co:
        if not any(tu.casefold() in thap for tu in nhom):
            return False, f"thiếu mọi cụm trong nhóm {nhom!r}"

    return True, ""


def doc_bang() -> dict[str, dict]:
    if not BANG.exists():
        return {}
    return json.loads(BANG.read_text(encoding="utf-8"))


def ghi_bang(bang: dict[str, dict]) -> None:
    BANG.parent.mkdir(parents=True, exist_ok=True)
    BANG.write_text(json.dumps(bang, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


async def main() -> int:
    if not client.san_sang():
        print(
            "Engine tư vấn chưa dùng được. Kiểm `ADVISOR_ENABLED` và "
            "`ADVISOR_API_KEY` trong backend/.env."
        )
        return 1

    model = settings.advisor_model
    gioi_han = 12
    chi_ma = None
    for arg in sys.argv[1:]:
        if arg.startswith("--gioi-han="):
            gioi_han = int(arg.split("=", 1)[1])
        elif arg.startswith("--ma="):
            chi_ma = arg.split("=", 1)[1]

    bang = {} if "--lam-lai" in sys.argv else doc_bang()
    ngu_canh = dung_ngu_canh()

    print(f"Model: {model}   |   giới hạn lượt gọi: {gioi_han}")
    print(f"Ngữ cảnh: đơn {MA_DON}, ứng viên 23 tuổi cao đẳng điều dưỡng, chưa học tiếng.")
    # In độ dài bốn khối: khối rỗng là lỗi dựng ngữ cảnh, và nó làm mọi ca đỏ
    # theo một cách trông như lỗi mô hình.
    for ten, khoi in ngu_canh.items():
        print(f"  {ten:14s} {len(khoi):5d} ký tự")
        if not khoi.strip():
            print(f"  KHỐI {ten} RỖNG — dừng, vì đo tiếp chỉ ra số liệu vô nghĩa.")
            return 1

    da_goi = 0
    khong_goi_duoc: list[str] = []
    for ca in BO_CA:
        if chi_ma and ca.ma != chi_ma:
            continue
        khoa = f"{model}::{ca.ma}"
        if khoa in bang and "--lam-lai" not in sys.argv and not chi_ma:
            continue
        if da_goi >= gioi_han:
            break

        cau, nguon = await qa.tra_loi(cau_hoi=ca.cau_hoi, **ngu_canh)
        da_goi += 1

        # Không gọi được mô hình thì **không ghi gì cả**. Đây là chốt chặn quan
        # trọng nhất của bộ đo này. Đo ngày 28/09: hạn mức cạn sau câu đầu tiên,
        # mười câu sau nhận câu ghép sẵn, và bảng ghi nhận chúng như kết quả thật
        # — ba ca còn chuyển sang ĐẠT, vì "không biết" tình cờ thỏa điều kiện của
        # chúng. Tức là mất mạng làm các ca "bot không bịa" xanh lên. Một bộ đo tự
        # khen mình khi hệ thống chết thì tệ hơn là không có bộ đo nào.
        if nguon == qa.NGUON_KHONG_GOI_DUOC:
            khong_goi_duoc.append(ca.ma)
            print(f"[bỏ qua] {ca.ma} — không gọi được mô hình, không ghi kết quả.")
            continue

        dat, vi_sao = cham(ca, cau, nguon)
        bang[khoa] = {
            "ma": ca.ma,
            "model": model,
            "cau_hoi": ca.cau_hoi,
            "cau_tra_loi": cau,
            "nguon": nguon,
            "dat": dat,
            "vi_sao": vi_sao,
        }
        ghi_bang(bang)  # Ghi từng ca: hết hạn mức giữa lượt cũng không mất.

    for m in sorted({row["model"] for row in bang.values()}):
        dat = hong = 0
        print(f"\n{'-' * 72}\nMODEL {m}")
        for ca in BO_CA:
            row = bang.get(f"{m}::{ca.ma}")
            if row is None:
                continue
            nhan = "ĐẠT " if row["dat"] else "HỎNG"
            dat, hong = (dat + 1, hong) if row["dat"] else (dat, hong + 1)
            print(f"\n[{nhan}] {ca.ma} · nguồn={row['nguon']}")
            print(f"   hỏi: {row['cau_hoi']}")
            print(f"   đáp: {row['cau_tra_loi'][:400]}")
            if not row["dat"]:
                print(f"   !! {row['vi_sao']}")
                print(f"   vì sao có ca này: {ca.vi_sao}")
        chua = len(BO_CA) - dat - hong
        print(f"\n  TỔNG trên {m}:  ĐẠT {dat}   HỎNG {hong}   CHƯA ĐO {chua}")

    models = sorted({row["model"] for row in bang.values()})
    if len(models) > 1:
        print(f"\n{'=' * 72}\nSO SÁNH — chỉ trên những ca mọi model đều đo được")
        chung = set.intersection(
            *[
                {row["ma"] for row in bang.values() if row["model"] == m}
                for m in models
            ]
        )
        print(f"{len(chung)} ca: {', '.join(sorted(chung))}\n")
        for m in models:
            dat = sum(
                1
                for row in bang.values()
                if row["model"] == m and row["ma"] in chung and row["dat"]
            )
            print(f"  {m:26s} ĐẠT {dat}/{len(chung)}")
        print("=" * 72)

    if khong_goi_duoc:
        print(
            f"\n{len(khong_goi_duoc)} ca không gọi được mô hình (hết hạn mức "
            f"hoặc dịch vụ quá tải): {', '.join(khong_goi_duoc)}.\n"
            f"Những ca này KHÔNG được ghi kết quả — chúng chưa được đo, chứ không "
            f"phải đo ra là hỏng."
        )

    con_no = [
        ca.ma for ca in BO_CA if f"{model}::{ca.ma}" not in bang
    ]
    if con_no:
        print(
            f"\nCòn {len(con_no)} ca chưa đo trên {model}: {', '.join(con_no)}.\n"
            f"Phần đã đo nằm ở {BANG.name}; chạy lại lệnh cũ là nó đo tiếp."
        )
    return 1 if con_no or any(not r["dat"] for r in bang.values()) else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
