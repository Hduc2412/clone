"""Nhập danh mục đơn tuyển dụng từ file Excel.

Doanh nghiệp đang quản lý đơn hàng bằng file Excel. Bắt nhân viên nhập lại từng
đơn trên màn hình web là cách chắc chắn nhất để danh mục không bao giờ được cập
nhật. Module này đọc thẳng file của họ.

Hai nguyên tắc:

1. **Xem trước rồi mới ghi.** Bộ nhập luôn trả về kết quả kiểm tra từng dòng
   trước, người dùng nhìn thấy dòng nào lỗi vì sao rồi mới bấm xác nhận. Một file
   hai trăm dòng mà ghi nửa chừng rồi báo lỗi là tình huống không dọn được.
2. **Sai thì báo, không đoán.** Ô ghi "Viện dưỡng lão" hay "vien duong lao" đều
   hiểu được, nhưng ô ghi "nhà hàng" thì báo lỗi chứ không tự chọn một giá trị
   gần đúng. Đây là dữ liệu quyết định ứng viên nào bị loại.

Cột được nhận diện theo **tiêu đề tiếng Việt ở hàng đầu**, không theo thứ tự, để
nhân viên chèn hay đổi chỗ cột mà file vẫn đọc được.
"""
from dataclasses import dataclass, field
from datetime import date, datetime
from io import BytesIO
from typing import Any, Callable

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from app.core.text import normalize_key
from app.core.timeutil import local_today
from app.matching import catalog


DATA_SHEET = "DonHang"
GUIDE_SHEET = "HuongDan"
CATALOG_SHEET = "DanhMuc"
SAMPLE_SHEET = "MauDuLieu"

MAX_ROWS = 500

# Màu phân biệt hai nhóm cột, để nhân viên nhìn là biết ô nào quyết định loại
# ứng viên và ô nào chỉ để hiển thị.
_HEADER_REQUIRED = PatternFill("solid", fgColor="FFC7CE")   # bắt buộc
_HEADER_HARD = PatternFill("solid", fgColor="FFE699")       # điều kiện cứng
_HEADER_NORMAL = PatternFill("solid", fgColor="D9E1F2")     # tham khảo


@dataclass(frozen=True)
class Column:
    label: str
    key: str
    required: bool = False
    hard: bool = False
    hint: str = ""
    width: int = 18


COLUMNS: tuple[Column, ...] = (
    Column("Mã đơn", "code", hint="Để trống khi thêm mới; điền mã khi muốn cập nhật", width=12),
    Column("Tên đơn", "title", required=True, hint="Ví dụ: Điều dưỡng viện dưỡng lão Tokyo", width=34),
    Column("Cơ sở tiếp nhận", "employer_name", required=True, hint="Tên cơ sở bên Nhật", width=26),
    Column("Loại hình", "employer_type", required=True, hint="Viện dưỡng lão / Bệnh viện / Chăm sóc tại gia", width=20),
    Column("Chương trình", "program", required=True, hint="EPA / Tokutei Ginou / Thực tập sinh", width=20),
    Column("Tỉnh", "prefecture", required=True, hint="Tên tỉnh tại Nhật, ví dụ Tokyo", width=14),
    Column("Thành phố", "city", hint="Không bắt buộc", width=16),
    Column("Số lượng", "quota", required=True, hint="Số người cần tuyển", width=10),
    Column("Tiếng Nhật tối thiểu", "japanese_required", required=True, hard=True, hint="N5 đến N1", width=18),
    Column("Bằng cấp tối thiểu", "education_required", hard=True, hint="Trung cấp / Cao đẳng / Đại học; để trống nếu không yêu cầu", width=18),
    Column("Kinh nghiệm tối thiểu (năm)", "experience_min", hard=True, hint="Để trống hoặc 0 nếu không yêu cầu", width=22),
    Column("Tuổi từ", "age_min", hard=True, width=10),
    Column("Tuổi đến", "age_max", hard=True, width=10),
    Column("Giới tính", "gender_pref", hard=True, hint="Nam / Nữ / Không yêu cầu", width=14),
    Column("Hạn nộp hồ sơ", "deadline", required=True, hard=True, hint="Dạng ngày, ví dụ 30/11/2026", width=16),
    Column("Lương từ (JPY)", "salary_min", hint="Lương cơ bản một tháng", width=15),
    Column("Lương đến (JPY)", "salary_max", width=15),
    Column("Phụ cấp", "allowances", hint="Nhiều mục cách nhau bằng dấu chấm phẩy", width=30),
    Column("Tổng chi phí (VND)", "cost_total_vnd", width=18),
    Column("Ngày phỏng vấn dự kiến", "interview_date", width=20),
    Column("Dự kiến xuất cảnh", "departure_expected", hint="Ví dụ 2027-03", width=18),
    Column("Điểm nổi bật", "highlights", hint="Nhiều mục cách nhau bằng dấu chấm phẩy", width=30),
    Column("Mô tả công việc", "description", width=40),
    Column("Trạng thái", "status", hint="Nháp / Đang tuyển", width=14),
    Column("Công khai", "published", hint="Có / Không", width=12),
    Column("Ghi chú nội bộ", "internal_note", hint="Không bao giờ hiển thị cho khách", width=28),
)

_COLUMN_BY_LABEL = {normalize_key(column.label): column for column in COLUMNS}


@dataclass
class RowResult:
    row_number: int
    action: str                      # "create" | "update" | "error"
    code: str | None = None
    title: str | None = None
    data: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "row_number": self.row_number,
            "action": self.action,
            "code": self.code,
            "title": self.title,
            "errors": self.errors,
            "data": self.data,
        }


@dataclass
class ImportPreview:
    rows: list[RowResult]
    missing_columns: list[str] = field(default_factory=list)

    @property
    def summary(self) -> dict[str, int]:
        return {
            "total": len(self.rows),
            "create": sum(1 for row in self.rows if row.action == "create"),
            "update": sum(1 for row in self.rows if row.action == "update"),
            "error": sum(1 for row in self.rows if row.action == "error"),
        }

    def as_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "missing_columns": self.missing_columns,
            "rows": [row.as_dict() for row in self.rows],
        }

    def valid_rows(self) -> list[RowResult]:
        return [row for row in self.rows if row.action != "error"]


# --- Đọc giá trị từng ô ---


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _int(value: Any, label: str, errors: list[str]) -> int | None:
    text = _text(value)
    if text is None:
        return None
    try:
        return int(float(text.replace(",", "").replace(".", "")))
    except ValueError:
        errors.append(f"{label}: '{text}' không phải là số.")
        return None


def _float(value: Any, label: str, errors: list[str]) -> float | None:
    text = _text(value)
    if text is None:
        return None
    try:
        return float(text.replace(",", "."))
    except ValueError:
        errors.append(f"{label}: '{text}' không phải là số.")
        return None


def _date(value: Any, label: str, errors: list[str]) -> date | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    for pattern in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            continue
    errors.append(f"{label}: '{text}' không đọc được thành ngày. Hãy dùng dạng 30/11/2026.")
    return None


def _bool(value: Any, label: str, errors: list[str]) -> bool | None:
    text = _text(value)
    if text is None:
        return None
    key = normalize_key(text)
    if key in {"co", "true", "1", "x", "yes", "cong khai"}:
        return True
    if key in {"khong", "false", "0", "no", "an"}:
        return False
    errors.append(f"{label}: '{text}' không hiểu. Hãy ghi Có hoặc Không.")
    return None


def _enum(
    value: Any,
    normalizer: Callable[[object], str | None],
    label: str,
    errors: list[str],
    *,
    allowed: dict[str, str],
) -> str | None:
    text = _text(value)
    if text is None:
        return None
    normalized = normalizer(text)
    if normalized is None:
        choices = " / ".join(allowed.values())
        errors.append(f"{label}: '{text}' không hợp lệ. Giá trị nhận: {choices}.")
    return normalized


def _list(value: Any) -> list[str]:
    text = _text(value)
    if text is None:
        return []
    separator = ";" if ";" in text else "\n"
    return [item.strip() for item in text.split(separator) if item.strip()]


# --- Đọc và kiểm tra một dòng ---


def parse_row(raw: dict[str, Any], row_number: int) -> RowResult:
    errors: list[str] = []
    result = RowResult(row_number=row_number, action="create")

    code = _text(raw.get("code"))
    title = _text(raw.get("title"))
    result.code = code
    result.title = title

    for column in COLUMNS:
        if column.required and _text(raw.get(column.key)) is None:
            errors.append(f"Thiếu {column.label.lower()}.")

    employer_type = _enum(
        raw.get("employer_type"), catalog.normalize_employer_type,
        "Loại hình", errors, allowed=catalog.EMPLOYER_TYPE_LABELS,
    )
    program = _enum(
        raw.get("program"), catalog.normalize_program,
        "Chương trình", errors, allowed=catalog.PROGRAM_LABELS,
    )
    prefecture = _enum(
        raw.get("prefecture"), catalog.normalize_prefecture,
        "Tỉnh", errors, allowed={"": "tên tỉnh tại Nhật Bản"},
    )

    japanese_cell = _text(raw.get("japanese_required"))
    japanese_levels = catalog.find_japanese_levels(japanese_cell)
    japanese_required = _enum(
        japanese_cell, catalog.normalize_japanese_level,
        "Tiếng Nhật tối thiểu", errors, allowed=catalog.JAPANESE_LEVEL_LABELS,
    )
    if len(japanese_levels) > 1:
        # Không tự chọn giúp: đây là điều kiện loại ứng viên, đoán sai một bậc là
        # loại oan cả một nhóm hồ sơ.
        errors.append(
            f"Tiếng Nhật tối thiểu: ô ghi nhiều mức ({', '.join(japanese_levels)}). "
            f"Hãy ghi đúng một mức bắt buộc."
        )

    education_required = None
    if _text(raw.get("education_required")):
        education_required = _enum(
            raw.get("education_required"), catalog.normalize_education,
            "Bằng cấp tối thiểu", errors, allowed=catalog.EDUCATION_LABELS,
        )

    gender_pref = "khong_yeu_cau"
    if _text(raw.get("gender_pref")):
        gender_pref = _enum(
            raw.get("gender_pref"), catalog.normalize_gender_pref,
            "Giới tính", errors, allowed=catalog.GENDER_PREF_LABELS,
        ) or "khong_yeu_cau"

    status = "draft"
    if _text(raw.get("status")):
        status = _enum(
            raw.get("status"), catalog.normalize_job_order_status,
            "Trạng thái", errors, allowed=catalog.JOB_ORDER_STATUS_LABELS,
        ) or "draft"
        if status not in {"draft", "open"}:
            errors.append(
                "Trạng thái: file nhập chỉ nhận Nháp hoặc Đang tuyển. "
                "Các trạng thái khác đổi trên màn hình quản trị để có lịch sử."
            )

    quota = _int(raw.get("quota"), "Số lượng", errors)
    if quota is not None and quota < 1:
        errors.append("Số lượng: phải lớn hơn 0.")

    age_min = _int(raw.get("age_min"), "Tuổi từ", errors)
    age_max = _int(raw.get("age_max"), "Tuổi đến", errors)
    if age_min is not None and age_max is not None and age_min > age_max:
        errors.append("Tuổi từ phải nhỏ hơn hoặc bằng tuổi đến.")

    salary_min = _int(raw.get("salary_min"), "Lương từ", errors)
    salary_max = _int(raw.get("salary_max"), "Lương đến", errors)
    if salary_min is not None and salary_max is not None and salary_min > salary_max:
        errors.append("Lương từ phải nhỏ hơn hoặc bằng lương đến.")

    deadline = _date(raw.get("deadline"), "Hạn nộp hồ sơ", errors)
    published = _bool(raw.get("published"), "Công khai", errors)

    # Ba trường này phải đọc trước bước kiểm lỗi bên dưới. Đọc chúng lúc dựng
    # `result.data` thì lỗi sinh ra ở đó rơi vào khoảng trống: danh sách lỗi đã
    # được xét xong, nên ô sai âm thầm biến thành rỗng thay vì báo cho người nhập.
    experience_min = _float(raw.get("experience_min"), "Kinh nghiệm tối thiểu", errors)
    cost_total_vnd = _int(raw.get("cost_total_vnd"), "Tổng chi phí", errors)
    interview_date = _date(raw.get("interview_date"), "Ngày phỏng vấn dự kiến", errors)
    if deadline and status == "open" and deadline < local_today():
        errors.append(
            f"Hạn nộp hồ sơ {deadline.strftime('%d/%m/%Y')} đã qua "
            f"nhưng trạng thái là Đang tuyển."
        )

    if errors:
        result.action = "error"
        result.errors = errors
        return result

    result.action = "update" if code else "create"
    result.data = {
        "title": title,
        "employer_name": _text(raw.get("employer_name")),
        "employer_type": employer_type,
        "program": program,
        "prefecture": prefecture,
        "region_group": catalog.region_for_prefecture(prefecture),
        "city": _text(raw.get("city")),
        "quota": quota,
        "deadline": deadline.isoformat(),
        "requirements": {
            "japanese_required": japanese_required,
            "education_required": education_required,
            "experience_min": experience_min or 0.0,
            "age_min": age_min,
            "age_max": age_max,
            "gender_pref": gender_pref,
        },
        "reference": {
            "salary_min": salary_min,
            "salary_max": salary_max,
            "allowances": _list(raw.get("allowances")),
            "cost_total_vnd": cost_total_vnd,
            "interview_date": interview_date.isoformat() if interview_date else None,
            "departure_expected": _text(raw.get("departure_expected")),
            "highlights": _list(raw.get("highlights")),
        },
        "description": _text(raw.get("description")),
        "internal_note": _text(raw.get("internal_note")),
        "status": status,
        "published": bool(published),
    }
    return result


def parse_workbook(content: bytes) -> ImportPreview:
    """Đọc file Excel thành danh sách dòng đã kiểm tra."""
    try:
        workbook = load_workbook(BytesIO(content), data_only=True, read_only=True)
    except Exception as exc:  # openpyxl ném nhiều loại lỗi khác nhau cho file hỏng
        raise ValueError("Không đọc được file Excel. Hãy lưu lại dạng .xlsx rồi thử lại.") from exc

    sheet = workbook[DATA_SHEET] if DATA_SHEET in workbook.sheetnames else workbook.worksheets[0]
    rows = sheet.iter_rows(values_only=True)
    try:
        header = next(rows)
    except StopIteration:
        return ImportPreview(rows=[], missing_columns=[c.label for c in COLUMNS if c.required])

    index_by_key: dict[str, int] = {}
    for position, cell in enumerate(header):
        label = _text(cell)
        if label is None:
            continue
        column = _COLUMN_BY_LABEL.get(normalize_key(label))
        if column is not None:
            index_by_key[column.key] = position

    missing = [
        column.label
        for column in COLUMNS
        if column.required and column.key not in index_by_key
    ]
    if missing:
        return ImportPreview(rows=[], missing_columns=missing)

    results: list[RowResult] = []
    seen_codes: dict[str, int] = {}
    for offset, values in enumerate(rows, start=2):
        if offset - 1 > MAX_ROWS:
            break
        raw = {
            key: (values[position] if position < len(values) else None)
            for key, position in index_by_key.items()
        }
        if all(_text(value) is None for value in raw.values()):
            continue
        result = parse_row(raw, row_number=offset)
        if result.code:
            previous = seen_codes.get(result.code)
            if previous is not None:
                result.action = "error"
                result.errors.append(
                    f"Mã đơn {result.code} bị lặp, đã xuất hiện ở dòng {previous}."
                )
            else:
                seen_codes[result.code] = offset
        results.append(result)

    workbook.close()
    return ImportPreview(rows=results)


# --- Sinh file mẫu ---


def build_template_workbook(include_samples: bool = True) -> Workbook:
    """Tạo file Excel mẫu để doanh nghiệp điền đơn hàng thật."""
    workbook = Workbook()

    guide = workbook.active
    guide.title = GUIDE_SHEET
    _write_guide(guide)

    sheet = workbook.create_sheet(DATA_SHEET)
    _write_header(sheet)

    catalog_sheet = workbook.create_sheet(CATALOG_SHEET)
    _write_catalog(catalog_sheet)
    _attach_validations(sheet, catalog_sheet)

    if include_samples:
        sample = workbook.create_sheet(SAMPLE_SHEET)
        _write_header(sample)
        _write_samples(sample)

    return workbook


def _write_header(sheet) -> None:
    for position, column in enumerate(COLUMNS, start=1):
        cell = sheet.cell(row=1, column=position, value=column.label)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        if column.required:
            cell.fill = _HEADER_REQUIRED
        elif column.hard:
            cell.fill = _HEADER_HARD
        else:
            cell.fill = _HEADER_NORMAL
        if column.hint:
            cell.comment = None  # chú thích để ở sheet hướng dẫn cho dễ in
        sheet.column_dimensions[get_column_letter(position)].width = column.width
    sheet.row_dimensions[1].height = 34
    sheet.freeze_panes = "A2"


def _write_guide(sheet) -> None:
    lines: list[tuple[str, str]] = [
        ("HƯỚNG DẪN NHẬP DANH MỤC ĐƠN TUYỂN DỤNG", ""),
        ("", ""),
        ("Nhập dữ liệu ở sheet", DATA_SHEET),
        ("Mỗi dòng là một đơn hàng. Hàng đầu là tiêu đề, đừng xóa.", ""),
        ("Sheet MauDuLieu là ví dụ đã điền sẵn, chỉ để tham khảo.", ""),
        ("", ""),
        ("MÀU TIÊU ĐỀ", ""),
        ("Hồng", "Bắt buộc điền, thiếu là dòng đó bị báo lỗi"),
        ("Vàng", "Điều kiện bắt buộc — dùng để loại ứng viên khi đối chiếu"),
        ("Xanh", "Thông tin tham khảo — chỉ để hiển thị và xếp hạng"),
        ("", ""),
        ("QUY TẮC", ""),
        ("Mã đơn", "Để trống khi thêm đơn mới. Điền mã khi muốn cập nhật đơn đã có."),
        ("Tiếng Nhật tối thiểu", "Ghi đúng một mức. Ô ghi 'N4 trở lên, ưu tiên N3' sẽ bị báo lỗi vì hệ thống không tự đoán mức bắt buộc."),
        ("Hạn nộp hồ sơ", "Ghi dạng ngày, ví dụ 30/11/2026. Hạn đã qua mà trạng thái Đang tuyển thì bị báo lỗi."),
        ("Phụ cấp, Điểm nổi bật", "Nhiều mục thì cách nhau bằng dấu chấm phẩy."),
        ("Trạng thái", "File nhập chỉ nhận Nháp hoặc Đang tuyển. Tạm dừng, đủ số lượng, đã đóng thì đổi trên màn hình quản trị để lưu được lịch sử."),
        ("Công khai", "Ghi Có hoặc Không. Đơn chỉ hiện trên website khi vừa Công khai, vừa Đang tuyển, vừa còn hạn."),
        ("Ghi chú nội bộ", "Không bao giờ hiển thị cho khách."),
        ("", ""),
        ("KHI NHẬP VÀO HỆ THỐNG", ""),
        ("Bước 1", "Tải file lên màn hình Đơn tuyển dụng, mục Nhập từ Excel."),
        ("Bước 2", "Xem bảng kiểm tra: dòng nào lỗi, lỗi gì. Chưa có gì được ghi ở bước này."),
        ("Bước 3", "Sửa lại file nếu cần, rồi bấm xác nhận để ghi vào hệ thống."),
        ("", ""),
        ("ĐẶT TÊN FILE CON", "DonHang_<MaDoiTac>_<NamThang>.xlsx, ví dụ DonHang_SAKURA_202609.xlsx"),
    ]
    for row_number, (left, right) in enumerate(lines, start=1):
        left_cell = sheet.cell(row=row_number, column=1, value=left)
        sheet.cell(row=row_number, column=2, value=right)
        if right == "" and left and not left.startswith(" "):
            left_cell.font = Font(bold=True)
    sheet.column_dimensions["A"].width = 26
    sheet.column_dimensions["B"].width = 96


def _catalog_values() -> list[tuple[str, list[str]]]:
    return [
        ("Loại hình", list(catalog.EMPLOYER_TYPE_LABELS.values())),
        ("Chương trình", list(catalog.PROGRAM_LABELS.values())),
        ("Tiếng Nhật", ["N5", "N4", "N3", "N2", "N1"]),
        ("Bằng cấp", ["Trung cấp", "Cao đẳng", "Đại học"]),
        ("Giới tính", list(catalog.GENDER_PREF_LABELS.values())),
        ("Trạng thái", ["Nháp", "Đang tuyển"]),
        ("Công khai", ["Có", "Không"]),
        ("Tỉnh", list(catalog.PREFECTURE_REGION)),
    ]


def _write_catalog(sheet) -> None:
    for position, (title, values) in enumerate(_catalog_values(), start=1):
        header = sheet.cell(row=1, column=position, value=title)
        header.font = Font(bold=True)
        for row_number, value in enumerate(values, start=2):
            sheet.cell(row=row_number, column=position, value=value)
        sheet.column_dimensions[get_column_letter(position)].width = 22


def _attach_validations(sheet, catalog_sheet) -> None:
    """Gắn ô chọn sẵn để nhân viên không phải gõ tay giá trị danh mục."""
    keys = (
        "employer_type",
        "program",
        "japanese_required",
        "education_required",
        "gender_pref",
        "status",
        "published",
        "prefecture",
    )
    position_by_key = {column.key: index for index, column in enumerate(COLUMNS, start=1)}
    for catalog_index, (key, (_, values)) in enumerate(
        zip(keys, _catalog_values()), start=1
    ):
        column_letter = get_column_letter(catalog_index)
        formula = (
            f"={CATALOG_SHEET}!${column_letter}$2:${column_letter}${len(values) + 1}"
        )
        validation = DataValidation(type="list", formula1=formula, allow_blank=True)
        sheet.add_data_validation(validation)
        target = get_column_letter(position_by_key[key])
        validation.add(f"{target}2:{target}{MAX_ROWS + 1}")


def _write_samples(sheet) -> None:
    from scripts.seed_data.job_orders_seed import JOB_ORDERS_SEED

    today = local_today()
    from datetime import timedelta

    for row_number, entry in enumerate(JOB_ORDERS_SEED[:15], start=2):
        deadline = today + timedelta(days=entry["deadline_in_days"])
        values = {
            "title": entry["title"],
            "employer_name": entry["employer_name"],
            "employer_type": catalog.EMPLOYER_TYPE_LABELS[entry["employer_type"]],
            "program": catalog.PROGRAM_LABELS[entry["program"]],
            "prefecture": entry["prefecture"],
            "city": entry.get("city"),
            "quota": entry["quota"],
            "japanese_required": entry["japanese_required"],
            "education_required": (
                catalog.EDUCATION_LABELS.get(entry.get("education_required") or "")
                or None
            ),
            "experience_min": entry.get("experience_min", 0),
            "age_min": entry.get("age_min"),
            "age_max": entry.get("age_max"),
            "gender_pref": catalog.GENDER_PREF_LABELS[entry.get("gender_pref", "khong_yeu_cau")],
            "deadline": deadline.strftime("%d/%m/%Y"),
            "salary_min": entry.get("salary_min"),
            "salary_max": entry.get("salary_max"),
            "allowances": "; ".join(entry.get("allowances", [])),
            "cost_total_vnd": entry.get("cost_total_vnd"),
            "departure_expected": entry.get("departure_expected"),
            "highlights": "; ".join(entry.get("highlights", [])),
            "description": entry.get("description"),
            "status": "Đang tuyển" if entry.get("status") == "open" else "Nháp",
            "published": "Có" if entry.get("published") else "Không",
        }
        for position, column in enumerate(COLUMNS, start=1):
            sheet.cell(row=row_number, column=position, value=values.get(column.key))


def template_bytes(include_samples: bool = True) -> bytes:
    buffer = BytesIO()
    build_template_workbook(include_samples=include_samples).save(buffer)
    return buffer.getvalue()
