"""Nghiệm thu bot tư vấn theo đơn: nó có bịa không, và nó có chịu nói không biết không.

Chạy:  venv/Scripts/python.exe -m scripts.nghiem_thu_tu_van

Cờ:
  --lam-lai              bỏ hết kết quả đã lưu, đo lại từ đầu
  --gioi-han=<n>         tối đa n lượt gọi mô hình trong lượt chạy này (mặc định 12)
  --ma=<MA>              chỉ đo đúng một ca, dùng khi vừa sửa prompt
  --model=<ten>          đo trên model khác thay vì `ADVISOR_MODEL`
  --khoa-chung           dùng `GEMINI_API_KEY` thay cho `ADVISOR_API_KEY`
  --nghi=<giay>          nghỉ giữa hai lượt gọi (mặc định 8)

## Vì sao có `--khoa-chung` và `--nghi`

Hạn mức gói miễn phí tính **theo dự án Google**, không theo khóa, và nó reset vào
nửa đêm giờ Thái Bình Dương — tức khoảng 14 giờ chiều theo giờ Việt Nam. Ngày
29/09 tôi mất một lúc mới hiểu vì sao "sang ngày mới" mà vẫn 429: theo giờ Việt
Nam thì đã qua ngày, còn theo giờ tính hạn mức thì chưa.

Hai khóa thuộc hai dự án khác nhau nên có hai hạn mức. `--khoa-chung` cho phép đo
tiếp bằng hạn mức còn lại của bên kia, và vì bảng kết quả ghi tên model vào từng
dòng, hai lượt đo ấy không trộn lẫn.

`--nghi` là vì còn một hàng rào thứ hai: số lượt mỗi phút. Bắn cả bộ liền không
nghỉ thì bị chặn ngay ở lượt thứ ba, và lúc ấy rất dễ kết luận sai là hết hạn mức
ngày.

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
import hashlib
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

import app  # noqa: F401  — đặt stdout về UTF-8 để in được tiếng Việt
from app.advisor import client, phrasing, qa
from app.core.config import settings
from app.consultation import advice as advice_builder
from app.consultation import eligibility, lien_he, order_context
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
        vi_sao=(
            "Đo 29/09: bot chỉ nêu khoảng tuổi của ĐƠN đang xét (20–35) và bỏ mất "
            "mức nền của chương trình (18–40). Người 37 tuổi hỏi câu này sẽ nghe "
            "'20–35' rồi kết luận cả chương trình đóng với mình, trong khi công ty "
            "nhận tới 40 tuổi và còn đơn khác. Đúng kiểu loại oan mà cả bộ đối "
            "chiếu dựng ra để tránh. Đây là lỗi đầu tiên bộ đo này tự tìm ra."
        ),
        phai_co=(("18",), ("40",), ("20", "35")),
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
            "Đo 29/09: bot nói 'chưa có thông tin' — đúng thiết kế nhưng sai thực "
            "tế. Công ty có giờ liên hệ rõ ràng, chỉ là nó khai trong "
            "`api/support.py` và không nằm trong khối dữ liệu nào đưa vào bot. "
            "Đã đưa vào qua `consultation/lien_he.py`; ca này canh để nó ở đó."
        ),
        phai_co=(("8h", "8 giờ"), ("17h", "17 giờ")),
        khong_duoc_co=("9h", "18h", "20h", "24/7"),
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
        # Phải ghép đúng như `api/consultation_room.py` ghép. Bộ đo dựng một
        # ngữ cảnh khác bản chạy thật thì nó đo một hệ thống không tồn tại —
        # và kết quả xanh của nó không nói gì về thứ ứng viên đang dùng.
        "dieu_kien_nen": "\n\n".join(
            (eligibility.render_muc_nen(), lien_he.render())
        ),
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


def dau_prompt() -> str:
    """Dấu nhận dạng của prompt hiện tại — tám ký tự đầu của băm SHA-256.

    Không có nó thì bảng kết quả nói dối theo một cách rất khó thấy: sửa prompt
    rồi mở bảng ra vẫn thấy HỎNG ở ca vừa sửa, vì dòng ấy đo trên prompt cũ.
    Gặp đúng chuyện đó ngày 29/09 — vừa siết prompt cho ca TU-01 thì hết hạn mức,
    và bảng in ra một kết quả trông như hiện tại mà thực ra đã cũ.

    Cùng một lỗi với việc phải ghi tên model vào từng dòng: bảng phải nói rõ mỗi
    con số đo trên cái gì, không thì mọi kết luận rút ra từ nó đều mất căn cứ.
    """
    # Băm cả prompt LẪN khối điều kiện nền. Đổi khối dữ liệu làm mọi phép đo trước
    # hết hiệu lực y như đổi prompt: ngày 29/09 tôi thêm giờ liên hệ vào khối ấy, và
    # nếu dấu nhận dạng chỉ băm prompt thì bảng vẫn hiện kết quả cũ như thể còn đúng.
    #
    # Cố ý KHÔNG băm khối đơn và khối đối chiếu: chúng chứa hạn nộp tính từ ngày
    # chạy, nên băm vào là mọi phép đo hết hiệu lực mỗi ngày — một thước đo không ai
    # dùng được. Hai khối kia là thứ mình chủ động sửa khi đổi hành vi của bot.
    #
    # Và băm cả **mã của các chốt hậu kiểm**. Lần thứ năm của cùng một sai sót,
    # phát hiện 29/09: ca BE-01 hiện HỎNG với câu cụt "Về điều kiện sức khỏe của
    # chương trình", trong khi chốt "câu chưa nói xong" đã bắt được câu ấy từ vài
    # giờ trước. Dòng kia đo trước khi có chốt, nhưng dấu nhận dạng không băm mã
    # chốt nên bảng coi nó vẫn còn hiệu lực.
    #
    # Chốt hậu kiểm quyết định ứng viên nhận câu nào — nó là một phần của "bot là
    # cái gì", đúng như prompt. Đổi chốt thì mọi phép đo trước hết hiệu lực.
    van = qa.PROMPT + eligibility.render_muc_nen() + lien_he.render() + _ma_chot()
    return hashlib.sha256(van.encode("utf-8")).hexdigest()[:8]


def _ma_chot() -> str:
    """Cấu trúc mã của hai module chốt hậu kiểm, bỏ chú thích và docstring.

    Băm `ast.dump` chứ không băm chuỗi nguồn: sửa một dấu phẩy trong chú thích thì
    không đổi hành vi của bot, mà lại làm mọi phép đo trước hết hiệu lực — thước đo
    nhiễu tới mức không ai dùng. Cây cú pháp bỏ qua chú thích sẵn; docstring thì
    phải bỏ tay.
    """
    import ast

    phan = []
    for mo_dun in (qa, phrasing):
        cay = ast.parse(Path(mo_dun.__file__).read_text(encoding="utf-8"))
        for nut in ast.walk(cay):
            if not isinstance(
                nut, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
            ):
                continue
            than = nut.body
            if (
                than
                and isinstance(than[0], ast.Expr)
                and isinstance(than[0].value, ast.Constant)
                and isinstance(than[0].value.value, str)
            ):
                nut.body = than[1:]
        phan.append(ast.dump(cay))
    return "".join(phan)


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
    nghi = 8.0
    for arg in sys.argv[1:]:
        if arg.startswith("--gioi-han="):
            gioi_han = int(arg.split("=", 1)[1])
        elif arg.startswith("--ma="):
            chi_ma = arg.split("=", 1)[1]
        elif arg.startswith("--model="):
            model = arg.split("=", 1)[1]
        elif arg.startswith("--nghi="):
            nghi = float(arg.split("=", 1)[1])
    settings.advisor_model = model

    if "--khoa-chung" in sys.argv:
        if not settings.gemini_api_key:
            print("GEMINI_API_KEY chưa khai trong backend/.env.")
            return 1
        # Ghi vào `advisor_api_key` chứ không sửa `client`: client đọc khóa riêng
        # trước, nên đây là cách đổi khóa mà không chạm mã chạy thật.
        settings.advisor_api_key = settings.gemini_api_key

    bang = {} if "--lam-lai" in sys.argv else doc_bang()
    ngu_canh = dung_ngu_canh()

    ten_khoa = "GEMINI_API_KEY" if "--khoa-chung" in sys.argv else "ADVISOR_API_KEY"
    print(f"Model: {model}   |   khóa: {ten_khoa}   |   "
          f"giới hạn lượt gọi: {gioi_han}   |   nghỉ {nghi}s giữa hai lượt")
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

        if da_goi:
            # Nghỉ giữa hai lượt. Hàng rào số lượt mỗi phút chặn sớm hơn hàng rào
            # mỗi ngày, và khi bị chặn thì thông báo lỗi không phân biệt hai loại.
            await asyncio.sleep(nghi)
        cau, nguon, model_da_tra = await qa.tra_loi(cau_hoi=ca.cau_hoi, **ngu_canh)
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
        # Khóa theo model ĐÃ TRẢ LỜI, không theo model được yêu cầu. Có dự phòng
        # thì hai thứ khác nhau, và khóa theo model yêu cầu thì bảng nhóm theo một
        # tên mà tra không ra dòng nào — đo được 3 ca vẫn hiện "CHƯA ĐO 11".
        # Gặp đúng lỗi này ngày 29/09, ngay lượt chạy đầu sau khi thêm dự phòng.
        khoa = f"{model_da_tra or model}::{ca.ma}"
        bang[khoa] = {
            "ma": ca.ma,
            # Model THẬT SỰ trả lời, không phải model được yêu cầu. Có dự phòng
            # thì hai thứ này khác nhau, và ghi sai thì cả bảng so sánh giữa hai
            # model mất nghĩa — đúng cái bẫy đã gặp ba lần trong hai ngày.
            "model": model_da_tra or model,
            "model_yeu_cau": model,
            "cau_hoi": ca.cau_hoi,
            "cau_tra_loi": cau,
            "nguon": nguon,
            "dat": dat,
            "vi_sao": vi_sao,
            "dau_prompt": dau_prompt(),
        }
        ghi_bang(bang)  # Ghi từng ca: hết hạn mức giữa lượt cũng không mất.

    cu_prompt_can_do_lai: list[str] = []
    for m in sorted({row["model"] for row in bang.values()}):
        dat = hong = 0
        print(f"\n{'-' * 72}\nMODEL {m}")
        for ca in BO_CA:
            row = bang.get(f"{m}::{ca.ma}")
            if row is None:
                continue
            # Kết quả đo trên prompt khác thì không nói được gì về prompt đang
            # chạy, dù đạt hay hỏng. Không tính vào tổng.
            cu = row.get("dau_prompt") != dau_prompt()
            if cu:
                nhan = "CŨ  "
                cu_prompt_can_do_lai.append(f"{m}::{ca.ma}")
            else:
                nhan = "ĐẠT " if row["dat"] else "HỎNG"
                dat, hong = (dat + 1, hong) if row["dat"] else (dat, hong + 1)
            print(f"\n[{nhan}] {ca.ma} · nguồn={row['nguon']}"
                  + ("  ← đo trên prompt CŨ, phải đo lại" if cu else ""))
            print(f"   hỏi: {row['cau_hoi']}")
            print(f"   đáp: {row['cau_tra_loi'][:400]}")
            if not row["dat"] and not cu:
                print(f"   !! {row['vi_sao']}")
                print(f"   vì sao có ca này: {ca.vi_sao}")
        chua = len(BO_CA) - dat - hong
        print(f"\n  TỔNG trên {m}:  ĐẠT {dat}   HỎNG {hong}   CHƯA ĐO {chua}")
        cu_cua_model = [x for x in cu_prompt_can_do_lai if x.startswith(f"{m}::")]
        if cu_cua_model:
            print(f"  ({len(cu_cua_model)} ca đo trên prompt cũ, tính là chưa đo: "
                  f"{', '.join(x.split('::')[1] for x in cu_cua_model)})")

    # Chỉ so trên những dòng đo bằng prompt ĐANG chạy. Một bảng so sánh trộn kết
    # quả của hai prompt khác nhau thì không so model với model nữa, mà so hai
    # phép đo không cùng điều kiện — và vì cả hai đều là con số, nhìn không ra.
    moi_nhat = {k: r for k, r in bang.items() if r.get("dau_prompt") == dau_prompt()}
    models = sorted({row["model"] for row in moi_nhat.values()})
    if len(models) > 1:
        print(f"\n{'=' * 72}\nSO SÁNH — chỉ trên những ca mọi model đều đo được")
        chung = set.intersection(
            *[
                {row["ma"] for row in moi_nhat.values() if row["model"] == m}
                for m in models
            ]
        )
        print(f"{len(chung)} ca: {', '.join(sorted(chung))}\n")
        for m in models:
            dat = sum(
                1
                for row in moi_nhat.values()
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
