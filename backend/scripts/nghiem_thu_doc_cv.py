"""Nghiệm thu bộ đọc CV: thông tin rút ra có đúng với bản gốc không.

Trả lời câu hỏi thứ ba trong `docs/design/13 §4`. Chạy bộ đọc trên sáu CV mẫu ở
`tests/fixtures/cv/` rồi đối chiếu từng trường với đáp án người viết ra trong
`dap_an.json`.

Chạy:  venv\\Scripts\\python.exe -m scripts.nghiem_thu_doc_cv

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
"""
import json
import sys
from pathlib import Path

import app  # noqa: F401  — đặt stdout về UTF-8 để in được tiếng Việt
from app.documents import extractor, reader


FIXTURES = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "cv"

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

DUNG, SAI, THIEU = "ĐÚNG", "SAI", "THIẾU"


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


def run_one(entry: dict) -> dict:
    path = FIXTURES / entry["file"]
    data = path.read_bytes()

    kind, read_result = reader.read(data, filename=entry["file"])
    if read_result.needs_model_ocr:
        return {
            "file": entry["file"],
            "unreadable": True,
            "failed": None,
            "rows": [],
            "rejected": {},
        }

    try:
        extraction = extractor.extract_fields(read_result.text)
    except extractor.ExtractionFailed as exc:
        # Hết hạn mức gọi mô hình hay mất mạng giữa chừng không được làm mất kết
        # quả của những CV đã đo xong. Ghi là "chưa đo được" rồi đi tiếp.
        return {
            "file": entry["file"],
            "unreadable": False,
            "failed": str(exc),
            "rows": [],
            "rejected": {},
        }

    rows = []
    for field, expected in sorted(entry["expected"].items()):
        if field in PREFERENCE_FIELDS:
            rows.append((field, expected, None, "NGOÀI PHẠM VI"))
            continue
        actual = extraction.fields.get(field)
        rows.append((field, expected, actual, compare(expected, actual)))

    return {
        "file": entry["file"],
        "unreadable": False,
        "failed": None,
        "rows": rows,
        "rejected": extraction.rejected,
        "evidence": extraction.evidence,
    }


def main() -> int:
    answers = json.loads((FIXTURES / "dap_an.json").read_text(encoding="utf-8"))
    results = [run_one(entry) for entry in answers]

    tong = {DUNG: 0, SAI: 0, THIEU: 0}
    sai_chi_tiet: list[str] = []
    chua_do: list[str] = []

    for entry, result in zip(answers, results):
        print(f"\n=== {result['file']} — {entry.get('note', '')}")
        if result["unreadable"]:
            print("    Bản scan, chưa rút được chữ. Hệ thống ghi nhận file và mời khai tay.")
            continue
        if result["failed"]:
            chua_do.append(result["file"])
            print(f"    CHƯA ĐO ĐƯỢC — {result['failed'][:110]}")
            continue

        for field, expected, actual, verdict in result["rows"]:
            if verdict in tong:
                tong[verdict] += 1
            mark = {DUNG: "  ", SAI: " !", THIEU: " ?"}.get(verdict, "  ")
            print(f"   {mark} {field:20s} mong đợi={str(expected):24s} đọc được={actual}")
            if verdict == SAI:
                sai_chi_tiet.append(
                    f"{result['file']} · {field}: mong đợi {expected!r}, đọc được {actual!r}"
                )

        if result["rejected"]:
            print("      không nhận:", result["rejected"])

    print("\n" + "=" * 72)
    print(f"ĐÚNG {tong[DUNG]}   SAI {tong[SAI]}   THIẾU {tong[THIEU]}")
    if chua_do:
        print(f"Chưa đo được {len(chua_do)} CV: {', '.join(chua_do)} — chạy lại khi có hạn mức.")
    if sai_chi_tiet:
        print("\nCác trường đọc sai — đây là phần cần xử lý:")
        for line in sai_chi_tiet:
            print("  -", line)
    else:
        print("Không trường nào đọc sai. Trường thiếu thì hệ thống hỏi lại ứng viên.")
    print("=" * 72)

    # Thoát khác 0 khi có trường đọc SAI. Trường THIẾU không làm hỏng nghiệm thu:
    # không biết thì hỏi là hành vi đúng, còn biết sai mới là hỏng.
    # Chưa đo được cũng coi là chưa đạt: một lượt nghiệm thu thiếu CV thì chưa
    # trả lời được câu hỏi đặt ra.
    return 1 if sai_chi_tiet or chua_do else 0


if __name__ == "__main__":
    sys.exit(main())
