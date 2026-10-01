"""Nghiệm thu bộ đọc CV: thông tin rút ra có đúng với bản gốc không.

Trả lời câu hỏi thứ ba trong `docs/design/13 §4`. Chạy bộ đọc trên tám CV mẫu ở
`tests/fixtures/cv/` rồi đối chiếu từng trường với đáp án người viết ra trong
`dap_an.json`.

Chạy:  venv/Scripts/python.exe -m scripts.nghiem_thu_doc_cv

Cờ:
  --lam-lai              bỏ hết kết quả đã lưu, đo lại từ đầu
  --model=<ten>          đo trên model khác thay vì `GEMINI_JSON_MODEL`
  --khoa-tu-van          dùng `ADVISOR_API_KEY` thay cho `GEMINI_API_KEY`

## Vì sao là script chứ không phải ca kiểm thử

Bộ này **gọi mô hình thật và cần mạng**. Bộ kiểm thử thường phải chạy được khi
hết hạn mức gọi mô hình và khi mất mạng, nên không nhét vào đó. Đây là việc chạy
tay trước mỗi mốc bàn giao, và kết quả đọc bằng mắt.

## Bốn cột kết quả, không phải một con số

- **ĐÚNG**  — máy đọc ra giá trị, khớp đáp án.
- **SAI**   — máy đọc ra giá trị, khác đáp án. Đây là cột duy nhất thật sự đáng lo:
  hồ sơ mang một con số không có trong CV.
- **THIẾU** — đáp án có, máy không dám nhận. Không nguy hiểm bằng SAI, vì hệ thống
  sẽ hỏi lại ứng viên. Nhưng nhiều quá thì bộ đọc thành vô dụng.
- **NGOÀI PHẠM VI** — trường nguyện vọng. Bộ đọc **cố ý không rút** những trường
  này khỏi CV: nguyện vọng phải do chính ứng viên nói ra, suy từ một tờ giấy là
  đoán hộ người khác. Đáp án có sẵn từ lúc dựng CV mẫu nên vẫn liệt kê ở đây, kèm
  ghi chú, để không ai tưởng là bộ đọc bỏ sót.

## Vì sao phải tích lũy kết quả qua nhiều đợt

Hạn mức gói miễn phí không đủ cho cả tám CV trong một lượt. Đo trên máy thật ngày
28/09: lượt chạy tắt ở CV thứ năm.

Điều đó sinh ra một cái bẫy đo lường **nguy hiểm hơn cả việc thiếu số liệu**. Mỗi
lượt chạy tắt ở một chỗ khác nhau, nên mỗi lượt đo **một tập CV khác nhau**. Đặt
hai bản tổng cạnh nhau rồi kết luận model nào đọc tốt hơn là so hai thứ không
cùng đơn vị — và vì cả hai đều là con số, không ai nhìn ra là đã so nhầm.

Nên bảng kết quả lưu từng CV kèm **tên model đã đo nó**, bồi dần qua nhiều đợt,
và phần so sánh giữa các model **chỉ tính trên những CV mọi model đều đo được**.
Thà so ít CV mà so đúng, hơn là so đủ tám CV mà so nhầm.
"""
import hashlib
import json
import sys
from pathlib import Path

import app  # noqa: F401  — đặt stdout về UTF-8 để in được tiếng Việt
from app.core.config import settings
from app.documents import extractor, reader


FIXTURES = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "cv"
KET_QUA = FIXTURES / "ket_qua_doc_cv.json"


def dau_van_tay() -> str:
    """Sáu ký tự nhận diện **cách đo**, không chỉ model đem đi đo.

    Bản trước đặt khóa là `model::file`. Prompt hay lược đồ trả về đổi thì bảng
    cũ vẫn khớp khóa, nên script bỏ qua hết và in ra một bảng số liệu **đo bằng
    một cách không còn tồn tại** — mà không có dấu hiệu nào để nhận ra.

    Đây đúng lỗi mà bộ đo lời tư vấn đã phải sửa hồi 29/09, và nó nguy hiểm hơn
    việc thiếu số liệu: thiếu thì biết là thiếu, còn số cũ trông y như số mới.

    Băm cả `PROMPT` lẫn `RESPONSE_SCHEMA` vì hai thứ này cùng quyết định bộ đọc
    nhận ra cái gì và được phép trả về cái gì. Đổi một trong hai là kết quả cũ
    hết hiệu lực.
    """
    noi_dung = extractor.PROMPT + "|" + json.dumps(
        extractor.RESPONSE_SCHEMA, ensure_ascii=False, sort_keys=True
    )
    return hashlib.sha256(noi_dung.encode("utf-8")).hexdigest()[:6]


# Nguyện vọng — xem docstring đầu file.
PREFERENCE_FIELDS = frozenset(
    {
        "desired_prefecture",
        "desired_region_group",
        "desired_employer_type",
        "salary_expectation_jpy",
        "budget_vnd",
    }
)

DUNG, SAI, THIEU, NGOAI = "ĐÚNG", "SAI", "THIẾU", "NGOÀI PHẠM VI"


def compare(expected, actual) -> str:
    # Đáp án ghi `None` nghĩa là CV **cố ý không nêu** trường này (xem CV số 05).
    # Máy cũng không nhận thì đó là đúng, không phải thiếu.
    if expected is None:
        return DUNG if actual is None else SAI
    if actual is None:
        return THIEU
    if isinstance(expected, float) or isinstance(actual, float):
        try:
            return DUNG if abs(float(expected) - float(actual)) < 0.01 else SAI
        except (TypeError, ValueError):
            return SAI
    if isinstance(expected, str) and isinstance(actual, str):
        return DUNG if expected.strip().casefold() == actual.strip().casefold() else SAI
    return DUNG if expected == actual else SAI


def run_one(entry: dict, model: str) -> dict:
    path = FIXTURES / entry["file"]
    data = path.read_bytes()
    chung = {"file": entry["file"], "model": model}

    kind, read_result = reader.read(data, filename=entry["file"])
    if read_result.needs_model_ocr:
        return {**chung, "unreadable": True, "failed": None, "rows": [], "rejected": {}}

    try:
        extraction = extractor.extract_fields(read_result.text)
    except extractor.ExtractionFailed as exc:
        # Hết hạn mức gọi mô hình hay mất mạng giữa chừng không được làm mất kết
        # quả của những CV đã đo xong. Ghi là "chưa đo được" rồi đi tiếp — và
        # **không lưu vào bảng**, để lượt sau đo lại đúng những CV này.
        return {**chung, "unreadable": False, "failed": str(exc), "rows": [], "rejected": {}}

    rows = []
    for field, expected in sorted(entry["expected"].items()):
        if field in PREFERENCE_FIELDS:
            rows.append([field, expected, None, NGOAI])
            continue
        actual = extraction.fields.get(field)
        rows.append([field, expected, actual, compare(expected, actual)])

    return {
        **chung,
        "unreadable": False,
        "failed": None,
        "rows": rows,
        "rejected": extraction.rejected,
    }


def doc_bang() -> dict[str, dict]:
    if not KET_QUA.exists():
        return {}
    return json.loads(KET_QUA.read_text(encoding="utf-8"))


def ghi_bang(bang: dict[str, dict]) -> None:
    KET_QUA.write_text(
        json.dumps(bang, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def dem(row: dict) -> dict[str, int]:
    tong = {DUNG: 0, SAI: 0, THIEU: 0}
    for _, _, _, verdict in row["rows"]:
        if verdict in tong:
            tong[verdict] += 1
    return tong


def in_so_sanh(bang: dict[str, dict]) -> None:
    """So các model trên **đúng tập CV mà mọi model đều đo được**.

    Đây là phần đáng tin duy nhất của bảng. Xem docstring đầu file.
    """
    models = sorted({row["model"] for row in bang.values()})
    if len(models) < 2:
        return

    do_duoc = {
        model: {
            row["file"]
            for row in bang.values()
            if row["model"] == model and not row["unreadable"]
        }
        for model in models
    }
    chung = set.intersection(*do_duoc.values())

    print("\n" + "=" * 72)
    print(f"SO SÁNH {len(models)} MODEL — chỉ trên {len(chung)} CV mà mọi model đều đo được")
    if not chung:
        print("  Chưa có CV nào mọi model đều đo xong. Chưa so được gì.")
        print("=" * 72)
        return
    for ten_file in sorted(chung):
        print(f"    {ten_file}")
    print()
    print(f"  {'model':26s} {'ĐÚNG':>6s} {'SAI':>5s} {'THIẾU':>7s}")
    for model in models:
        tong = {DUNG: 0, SAI: 0, THIEU: 0}
        for row in bang.values():
            if row["model"] == model and row["file"] in chung:
                for khoa, so in dem(row).items():
                    tong[khoa] += so
        print(f"  {model:26s} {tong[DUNG]:6d} {tong[SAI]:5d} {tong[THIEU]:7d}")
    # Số CV mỗi model đo lẻ, để người đọc biết bảng trên đã đủ căn cứ chưa.
    for model in models:
        le = len(do_duoc[model] - chung)
        if le:
            print(
                f"  ({model}: {le} CV đo rồi nhưng model khác chưa — "
                f"không tính vào bảng trên)"
            )
    print("=" * 72)


def main() -> int:
    answers = json.loads((FIXTURES / "dap_an.json").read_text(encoding="utf-8"))

    model = settings.gemini_json_model
    for arg in sys.argv[1:]:
        if arg.startswith("--model="):
            model = arg.split("=", 1)[1]
    settings.gemini_json_model = model

    dung_khoa_tu_van = "--khoa-tu-van" in sys.argv
    if dung_khoa_tu_van:
        if not settings.advisor_api_key:
            print("ADVISOR_API_KEY chưa khai trong backend/.env.")
            return 1
        settings.gemini_api_key = settings.advisor_api_key

    bang = {} if "--lam-lai" in sys.argv else doc_bang()
    ten_khoa = "ADVISOR_API_KEY" if dung_khoa_tu_van else "GEMINI_API_KEY"
    print(f"Model: {model}   |   khóa: {ten_khoa}")

    sai_chi_tiet: list[str] = []
    chua_do: list[str] = []
    bo_qua = 0

    van_tay = dau_van_tay()
    print(f"Dấu vân tay cách đo: {van_tay} (prompt + lược đồ trả về)")

    van_tay_cu = sorted(
        {k.split("::")[1] for k in bang if k.count("::") == 2 and k.split("::")[1] != van_tay}
    )
    doi_khoa_cu = sum(1 for k in bang if k.count("::") < 2)
    if van_tay_cu or doi_khoa_cu:
        phan = []
        if van_tay_cu:
            phan.append(f"cách đo khác: {', '.join(van_tay_cu)}")
        if doi_khoa_cu:
            phan.append(f"{doi_khoa_cu} dòng đo khi chưa ghi dấu vân tay")
        print(
            "Bảng còn kết quả cũ (" + "; ".join(phan) + ") — "
            "những dòng ấy KHÔNG tính vào bảng dưới."
        )

    for entry in answers:
        khoa = f"{model}::{van_tay}::{entry['file']}"
        if khoa in bang:
            bo_qua += 1
            continue
        result = run_one(entry, model)
        if result["failed"]:
            chua_do.append(result["file"])
            print(f"\n=== {result['file']}\n    CHƯA ĐO ĐƯỢC — {result['failed'][:110]}")
            continue
        bang[khoa] = result
        # Ghi ngay từng CV. Hết hạn mức giữa lượt cũng không mất phần đã đo.
        ghi_bang(bang)

    if bo_qua:
        print(f"Bỏ qua {bo_qua} CV đã đo trên {model} (dùng --lam-lai để đo lại).")

    # Chỉ tổng hợp những dòng đo bằng đúng cách đo hiện tại. Dòng cũ vẫn giữ
    # trong tệp để đối chiếu khi cần, nhưng không được trộn vào bảng.
    dung_cach = {k: v for k, v in bang.items() if k.split("::")[1:2] == [van_tay]}
    for m in sorted({row["model"] for row in dung_cach.values()}):
        tong = {DUNG: 0, SAI: 0, THIEU: 0}
        print(f"\n{'-' * 72}\nMODEL {m}   ·   cách đo {van_tay}")
        for entry in answers:
            row = bang.get(f"{m}::{van_tay}::{entry['file']}")
            if row is None:
                continue
            print(f"\n=== {row['file']} — {entry.get('note', '')}")
            if row["unreadable"]:
                print("    Bản scan, chưa rút được chữ. Hệ thống ghi nhận file và mời khai tay.")
                continue
            for field, expected, actual, verdict in row["rows"]:
                if verdict in tong:
                    tong[verdict] += 1
                mark = {DUNG: "  ", SAI: " !", THIEU: " ?"}.get(verdict, "  ")
                print(f"   {mark} {field:20s} mong đợi={str(expected):24s} đọc được={actual}")
                if verdict == SAI:
                    sai_chi_tiet.append(
                        f"{m} · {row['file']} · {field}: "
                        f"mong đợi {expected!r}, đọc được {actual!r}"
                    )
            if row["rejected"]:
                print("      không nhận:", row["rejected"])
        print(f"\n  TỔNG trên {m}:  ĐÚNG {tong[DUNG]}   SAI {tong[SAI]}   THIẾU {tong[THIEU]}")

    in_so_sanh(bang)

    if sai_chi_tiet:
        print("\nCác trường đọc sai — đây là phần cần xử lý:")
        for line in sai_chi_tiet:
            print("  -", line)
    else:
        print("\nKhông trường nào đọc sai. Trường thiếu thì hệ thống hỏi lại ứng viên.")
    if chua_do:
        print(
            f"\nChưa đo được {len(chua_do)} CV: {', '.join(chua_do)}.\n"
            f"Phần đã đo nằm ở {KET_QUA.name}; chạy lại lệnh cũ là nó đo tiếp đúng "
            f"những CV còn nợ, không đo lại từ đầu."
        )

    # Thoát khác 0 khi có trường đọc SAI. Trường THIẾU không làm hỏng nghiệm thu:
    # không biết thì hỏi là hành vi đúng, còn biết sai mới là hỏng.
    # Chưa đo được cũng coi là chưa đạt: một lượt nghiệm thu thiếu CV thì chưa
    # trả lời được câu hỏi đặt ra.
    return 1 if sai_chi_tiet or chua_do else 0


if __name__ == "__main__":
    sys.exit(main())
