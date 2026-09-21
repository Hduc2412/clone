"""Bộ đối chiếu hồ sơ ứng viên với đơn tuyển dụng.

Đây là phần lõi của đề tài. Toàn bộ module **thuần tính toán**: không đọc đồng hồ,
không chạm database, không gọi mô hình ngôn ngữ. `as_of` và `weights` là tham số
truyền vào chứ không phải thứ hàm tự đi lấy.

Nhờ vậy cùng một hồ sơ và cùng một danh mục đơn luôn cho ra cùng một kết quả, kiểm
thử được bằng cách chạy hai lần rồi so từng byte, và sáu tháng sau vẫn dựng lại
được đúng kết quả cũ để giải trình.

## Hai loại tiêu chí

**Điều kiện bắt buộc** đọc từ `fields` của hồ sơ, tức những thứ kiểm chứng được
trên giấy tờ. Mỗi tiêu chí sinh đúng một dòng.

**Xếp hạng mềm** đọc từ `preferences`, tức nguyện vọng do ứng viên nói. Tách hai
nguồn dữ liệu ở hai hàm khác nhau là để một nguyện vọng **không bao giờ** loại
được ai, kể cả khi có người sửa nhầm code về sau.

## Quy tắc trung tâm: chỉ loại khi chắc chắn

Thiếu dữ liệu của ứng viên cho ra `CHUA_RO` và **không loại đơn**. Người chưa khai
năm sinh không phải người quá tuổi, ta chỉ là chưa biết. Nếu loại theo cái chưa
biết thì một hồ sơ mới điền một nửa sẽ ra không đơn nào, và tệ hơn là giấu mất đơn
thật sự phù hợp với một ứng viên thật. Cái chưa biết được đẩy thành câu hỏi trong
`missing_info` để hỏi tiếp.

Ngược lại, **đơn hàng** thiếu trạng thái hay hạn nộp thì hỏng là loại. Bản ghi lỗi
không được đem đi giới thiệu cho ai.
"""
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Sequence

from app.core.timeutil import age_on
from app.matching import catalog
from app.matching.weights import Weights


ENGINE_VERSION = "1.0.0"

DAT = "DAT"
KHONG_DAT = "KHONG_DAT"
CHUA_RO = "CHUA_RO"

HARD_KEYS: tuple[str, ...] = (
    "status",
    "deadline",
    "japanese",
    "education",
    "experience",
    "age",
    "gender",
)
SOFT_KEYS: tuple[str, ...] = ("region", "employer_type", "salary", "cost")

# Thứ tự cố định khi gộp câu hỏi còn thiếu. Không dùng thứ tự của tập hợp, vì tập
# hợp trong Python không bảo đảm thứ tự ổn định giữa các lần chạy.
MISSING_ORDER: tuple[str, ...] = (
    "japanese_level",
    "education_level",
    "experience_years",
    "birth_year",
    "gender",
    "desired_prefecture",
    "desired_employer_type",
    "salary_expectation_jpy",
    "budget_vnd",
)

MISSING_PROMPTS: dict[str, str] = {
    "japanese_level": "Bạn cho biết trình độ tiếng Nhật hiện tại, hoặc chưa học, để hệ thống lọc chính xác hơn.",
    "education_level": "Bạn cho biết bằng cấp cao nhất đang có.",
    "experience_years": "Bạn cho biết số năm kinh nghiệm chăm sóc hoặc điều dưỡng.",
    "birth_year": "Bạn cho biết năm sinh để đối chiếu khoảng tuổi của đơn hàng.",
    "gender": "Bạn cho biết giới tính, vì một số đơn chỉ tuyển nam hoặc chỉ tuyển nữ.",
    "desired_prefecture": "Bạn muốn làm việc ở khu vực nào tại Nhật Bản?",
    "desired_employer_type": "Bạn muốn làm viện dưỡng lão, bệnh viện hay chăm sóc tại gia?",
    "salary_expectation_jpy": "Bạn mong muốn mức lương khoảng bao nhiêu mỗi tháng?",
    "budget_vnd": "Bạn có thể chuẩn bị khoảng bao nhiêu chi phí?",
}


# --- Kiểu dữ liệu ---


@dataclass(frozen=True)
class CandidateFacts:
    """Ảnh chụp hồ sơ tại một thời điểm, đã chuẩn hóa và tính sẵn thứ hạng."""

    profile_code: str = ""
    profile_version: int = 0
    japanese_level: str | None = None
    japanese_rank: int | None = None
    education_level: str | None = None
    education_rank: int | None = None
    experience_years: float | None = None
    birth_year: int | None = None
    age: int | None = None
    gender: str | None = None
    care_experience: bool | None = None
    desired_prefecture: str | None = None
    desired_region_group: str | None = None
    desired_employer_type: str | None = None
    salary_expectation_jpy: int | None = None
    budget_vnd: int | None = None


@dataclass(frozen=True)
class CriterionRow:
    key: str
    label: str
    requirement_text: str
    candidate_text: str
    result: str
    missing_field: str | None = None
    kind: str = "cung"

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "requirement_text": self.requirement_text,
            "candidate_text": self.candidate_text,
            "result": self.result,
            "result_label": catalog.RESULT_LABELS.get(self.result, self.result),
            "missing_field": self.missing_field,
            "kind": self.kind,
        }


@dataclass(frozen=True)
class SoftRow:
    key: str
    label: str
    requirement_text: str
    candidate_text: str
    outcome: str
    points: int
    max_points: int
    missing_field: str | None = None
    kind: str = "mem"

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "requirement_text": self.requirement_text,
            "candidate_text": self.candidate_text,
            "outcome": self.outcome,
            "points": self.points,
            "max_points": self.max_points,
            "missing_field": self.missing_field,
            "kind": self.kind,
        }


@dataclass(frozen=True)
class MatchItem:
    code: str
    title: str
    employer_name: str
    prefecture: str
    region_group: str | None
    employer_type: str
    program: str
    deadline: str
    eligible: bool
    score: int
    rank: int | None
    hard_rows: tuple[CriterionRow, ...]
    soft_rows: tuple[SoftRow, ...]
    gaps: tuple[str, ...]
    missing_info: tuple[str, ...]
    labels: dict[str, str | None] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "title": self.title,
            "employer_name": self.employer_name,
            "prefecture": self.prefecture,
            "region_group": self.region_group,
            "employer_type": self.employer_type,
            "program": self.program,
            "deadline": self.deadline,
            "eligible": self.eligible,
            "score": self.score,
            "rank": self.rank,
            "hard_rows": [row.as_dict() for row in self.hard_rows],
            "soft_rows": [row.as_dict() for row in self.soft_rows],
            "gaps": list(self.gaps),
            "missing_info": list(self.missing_info),
            "labels": self.labels,
        }


@dataclass(frozen=True)
class MatchResult:
    as_of: str
    engine_version: str
    weights_version: str
    weights_fingerprint: str
    profile_code: str
    profile_version: int
    total_considered: int
    eligible_count: int
    items: tuple[MatchItem, ...]
    missing_info: tuple[str, ...]

    def top(self, limit: int) -> tuple[MatchItem, ...]:
        return tuple(item for item in self.items if item.eligible)[:limit]

    def as_dict(self) -> dict[str, Any]:
        return {
            "as_of": self.as_of,
            "engine_version": self.engine_version,
            "weights_version": self.weights_version,
            "weights_fingerprint": self.weights_fingerprint,
            "profile_code": self.profile_code,
            "profile_version": self.profile_version,
            "total_considered": self.total_considered,
            "eligible_count": self.eligible_count,
            "items": [item.as_dict() for item in self.items],
            "missing_info": list(self.missing_info),
        }


# --- Đọc hồ sơ ---


def value_of(section: dict[str, Any] | None, key: str) -> Any:
    """Lấy giá trị một trường. Trường vắng mặt và trường rỗng đều là chưa rõ."""
    if not section:
        return None
    cell = section.get(key)
    if not isinstance(cell, dict):
        return cell if cell not in ("", None) else None
    value = cell.get("value")
    return value if value not in ("", None) else None


def build_facts(profile: dict[str, Any], as_of: date) -> CandidateFacts:
    fields = profile.get("fields") or {}
    preferences = profile.get("preferences") or {}

    # Chuẩn hóa lại một lần nữa dù API đã chuẩn hóa lúc ghi: giá trị có thể do
    # nhân viên nhập thẳng vào database hoặc do bộ đọc CV ghi, không đi qua API.
    japanese_level = catalog.normalize_japanese_level(value_of(fields, "japanese_level"))
    education_level = catalog.normalize_education(value_of(fields, "education_level"))
    gender = catalog.normalize_gender(value_of(fields, "gender"))

    birth_year = value_of(fields, "birth_year")
    birth_year = int(birth_year) if isinstance(birth_year, (int, float)) else None
    experience = value_of(fields, "experience_years")
    experience = float(experience) if isinstance(experience, (int, float)) else None

    desired_prefecture = catalog.normalize_prefecture(
        value_of(preferences, "desired_prefecture")
    )
    desired_region = catalog.normalize_region(
        value_of(preferences, "desired_region_group")
    )
    # Nêu tỉnh là đủ; vùng suy ra được. Bắt ứng viên chọn cả hai chỉ tạo cơ hội
    # để hai giá trị mâu thuẫn nhau.
    if desired_region is None and desired_prefecture:
        desired_region = catalog.region_for_prefecture(desired_prefecture)

    salary = value_of(preferences, "salary_expectation_jpy")
    budget = value_of(preferences, "budget_vnd")

    return CandidateFacts(
        profile_code=profile.get("code", ""),
        profile_version=int(profile.get("version", 0) or 0),
        japanese_level=japanese_level,
        japanese_rank=catalog.JAPANESE_RANK.get(japanese_level) if japanese_level else None,
        education_level=education_level,
        education_rank=catalog.EDUCATION_RANK.get(education_level) if education_level else None,
        experience_years=experience,
        birth_year=birth_year,
        age=age_on(birth_year, as_of),
        gender=gender,
        care_experience=value_of(fields, "care_experience"),
        desired_prefecture=desired_prefecture,
        desired_region_group=desired_region,
        desired_employer_type=catalog.normalize_employer_type(
            value_of(preferences, "desired_employer_type")
        ),
        salary_expectation_jpy=int(salary) if isinstance(salary, (int, float)) else None,
        budget_vnd=int(budget) if isinstance(budget, (int, float)) else None,
    )


# --- Trình bày số ---


def format_years(value: float) -> str:
    """2.0 thành "2", 1.5 thành "1,5". Dấu phẩy thập phân theo cách viết tiếng Việt."""
    if value == int(value):
        return str(int(value))
    return f"{value:.1f}".replace(".", ",")


def format_date(value: date) -> str:
    """Ngày viết theo lối người Việt đọc, không phải lối máy lưu.

    Thẻ đơn hàng trên website in `31/10/2026`. Bảng tiêu chí trước đây in
    `2026-10-31` cho cùng cái ngày ấy, và hai thứ nằm cạnh nhau trên một màn
    hình. Người đọc phải dừng lại kiểm xem có phải cùng một ngày không — đúng
    kiểu nghi ngờ mà một bảng đối chiếu không nên gây ra.
    """
    return value.strftime("%d/%m/%Y")


def format_thousand(value: int) -> str:
    return f"{value:,}".replace(",", ".")


def age_range_text(age_min: int | None, age_max: int | None) -> str:
    if age_min and age_max:
        return f"tuổi {age_min}–{age_max}"
    if age_min:
        return f"từ {age_min} tuổi"
    if age_max:
        return f"đến {age_max} tuổi"
    return "không giới hạn tuổi"


# --- Điều kiện bắt buộc ---


def evaluate_hard(
    order: dict[str, Any],
    facts: CandidateFacts,
    as_of: date,
) -> list[CriterionRow]:
    """Luôn trả về đúng bảy dòng, đúng thứ tự `HARD_KEYS`.

    Số dòng cố định là có chủ ý: màn hình nhật ký giới thiệu và khối giải thích
    đều dựa vào đó, và người đọc thấy ngay tiêu chí nào đã được xét chứ không
    phải đoán xem tiêu chí vắng mặt nghĩa là đạt hay là không xét.
    """
    requirements = order.get("requirements") or {}
    rows: list[CriterionRow] = []

    # 1. Trạng thái đơn
    status = order.get("status")
    rows.append(
        CriterionRow(
            key="status",
            label="Trạng thái đơn",
            requirement_text="đơn phải đang tuyển",
            candidate_text=f"đơn: {catalog.JOB_ORDER_STATUS_LABELS.get(status, 'không rõ')}",
            result=DAT if status == "open" else KHONG_DAT,
        )
    )

    # 2. Hạn nộp
    deadline_raw = order.get("deadline")
    try:
        deadline = date.fromisoformat(str(deadline_raw))
        deadline_ok = deadline >= as_of
        deadline_text = f"hạn nộp {format_date(deadline)}"
    except (TypeError, ValueError):
        deadline_ok = False
        deadline_text = "hạn nộp không hợp lệ"
    rows.append(
        CriterionRow(
            key="deadline",
            label="Hạn nộp hồ sơ",
            requirement_text=deadline_text,
            candidate_text=f"hôm nay {format_date(as_of)}",
            result=DAT if deadline_ok else KHONG_DAT,
        )
    )

    # 3. Tiếng Nhật
    required_japanese = requirements.get("japanese_required")
    required_rank = catalog.JAPANESE_RANK.get(required_japanese)
    if facts.japanese_rank is None:
        japanese_result, japanese_missing = CHUA_RO, "japanese_level"
        japanese_candidate = "chưa rõ trình độ"
    else:
        japanese_missing = None
        japanese_candidate = f"ứng viên {catalog.JAPANESE_LEVEL_LABELS.get(facts.japanese_level, facts.japanese_level)}"
        japanese_result = (
            DAT if required_rank is None or facts.japanese_rank >= required_rank else KHONG_DAT
        )
    rows.append(
        CriterionRow(
            key="japanese",
            label="Tiếng Nhật",
            requirement_text=(
                f"yêu cầu {catalog.JAPANESE_LEVEL_LABELS.get(required_japanese, required_japanese)}"
                if required_japanese
                else "không yêu cầu tiếng Nhật"
            ),
            candidate_text=japanese_candidate,
            result=japanese_result,
            missing_field=japanese_missing,
        )
    )

    # 4. Bằng cấp
    required_education = requirements.get("education_required")
    if not required_education:
        education_result, education_missing = DAT, None
        education_candidate = (
            f"có bằng {catalog.EDUCATION_LABELS.get(facts.education_level)}"
            if facts.education_level
            else "không cần xét"
        )
    elif facts.education_rank is None:
        education_result, education_missing = CHUA_RO, "education_level"
        education_candidate = "chưa rõ bằng cấp"
    else:
        education_missing = None
        education_candidate = f"có bằng {catalog.EDUCATION_LABELS.get(facts.education_level)}"
        required_rank = catalog.EDUCATION_RANK.get(required_education, 0)
        education_result = DAT if facts.education_rank >= required_rank else KHONG_DAT
    rows.append(
        CriterionRow(
            key="education",
            label="Bằng cấp",
            requirement_text=(
                f"cần bằng {catalog.EDUCATION_LABELS.get(required_education)}"
                if required_education
                else "không yêu cầu bằng cấp"
            ),
            candidate_text=education_candidate,
            result=education_result,
            missing_field=education_missing,
        )
    )

    # 5. Kinh nghiệm
    required_experience = float(requirements.get("experience_min") or 0)
    if required_experience <= 0:
        experience_result, experience_missing = DAT, None
        experience_candidate = (
            f"có {format_years(facts.experience_years)} năm"
            if facts.experience_years is not None
            else "không cần xét"
        )
    elif facts.experience_years is None:
        experience_result, experience_missing = CHUA_RO, "experience_years"
        experience_candidate = "chưa rõ kinh nghiệm"
    else:
        experience_missing = None
        experience_candidate = f"có {format_years(facts.experience_years)} năm"
        experience_result = DAT if facts.experience_years >= required_experience else KHONG_DAT
    rows.append(
        CriterionRow(
            key="experience",
            label="Kinh nghiệm",
            requirement_text=(
                f"cần {format_years(required_experience)} năm kinh nghiệm"
                if required_experience > 0
                else "không yêu cầu kinh nghiệm"
            ),
            candidate_text=experience_candidate,
            result=experience_result,
            missing_field=experience_missing,
        )
    )

    # 6. Độ tuổi
    age_min = requirements.get("age_min")
    age_max = requirements.get("age_max")
    if age_min is None and age_max is None:
        age_result, age_missing = DAT, None
        age_candidate = f"{facts.age} tuổi" if facts.age is not None else "không cần xét"
    elif facts.age is None:
        age_result, age_missing = CHUA_RO, "birth_year"
        age_candidate = "chưa rõ năm sinh"
    else:
        age_missing = None
        age_candidate = f"{facts.age} tuổi"
        within = (age_min is None or facts.age >= age_min) and (
            age_max is None or facts.age <= age_max
        )
        age_result = DAT if within else KHONG_DAT
    rows.append(
        CriterionRow(
            key="age",
            label="Độ tuổi",
            requirement_text=age_range_text(age_min, age_max),
            candidate_text=age_candidate,
            result=age_result,
            missing_field=age_missing,
        )
    )

    # 7. Giới tính
    gender_pref = requirements.get("gender_pref") or "khong_yeu_cau"
    if gender_pref == "khong_yeu_cau":
        gender_result, gender_missing = DAT, None
        gender_candidate = (
            f"ứng viên {catalog.GENDER_LABELS.get(facts.gender)}"
            if facts.gender
            else "không cần xét"
        )
    elif facts.gender is None:
        gender_result, gender_missing = CHUA_RO, "gender"
        gender_candidate = "chưa rõ giới tính"
    else:
        gender_missing = None
        gender_candidate = f"ứng viên {catalog.GENDER_LABELS.get(facts.gender)}"
        gender_result = DAT if facts.gender == gender_pref else KHONG_DAT
    rows.append(
        CriterionRow(
            key="gender",
            label="Giới tính",
            requirement_text=(
                f"yêu cầu {catalog.GENDER_PREF_LABELS.get(gender_pref)}"
                if gender_pref != "khong_yeu_cau"
                else "không yêu cầu giới tính"
            ),
            candidate_text=gender_candidate,
            result=gender_result,
            missing_field=gender_missing,
        )
    )

    return rows


def is_eligible(rows: Sequence[CriterionRow]) -> bool:
    """Đạt khi không có dòng nào không đạt. Dòng chưa rõ **không** loại đơn."""
    return not any(row.result == KHONG_DAT for row in rows)


# --- Xếp hạng mềm ---


def evaluate_soft(
    order: dict[str, Any],
    facts: CandidateFacts,
    weights: Weights,
) -> list[SoftRow]:
    """Luôn trả về đúng bốn dòng, đúng thứ tự `SOFT_KEYS`."""
    reference = order.get("reference") or {}
    rows: list[SoftRow] = []

    # 1. Khu vực
    prefecture = order.get("prefecture")
    region_group = order.get("region_group")
    if facts.desired_prefecture is None and facts.desired_region_group is None:
        region_outcome, region_missing = "unknown", "desired_prefecture"
        region_candidate = "chưa nêu nguyện vọng"
    elif facts.desired_prefecture and facts.desired_prefecture == prefecture:
        region_outcome, region_missing = "same_prefecture", None
        region_candidate = f"mong muốn {facts.desired_prefecture}"
    elif facts.desired_region_group and facts.desired_region_group == region_group:
        region_outcome, region_missing = "same_region", None
        region_candidate = f"mong muốn vùng {catalog.REGION_LABELS.get(facts.desired_region_group)}"
    else:
        region_outcome, region_missing = "different", None
        region_candidate = f"mong muốn {facts.desired_prefecture or catalog.REGION_LABELS.get(facts.desired_region_group)}"
    rows.append(
        SoftRow(
            key="region",
            label="Khu vực",
            requirement_text=f"khu vực {prefecture}",
            candidate_text=region_candidate,
            outcome=region_outcome,
            points=weights.points("region", region_outcome),
            max_points=weights.max_points("region"),
            missing_field=region_missing,
        )
    )

    # 2. Loại hình cơ sở
    employer_type = order.get("employer_type")
    if facts.desired_employer_type is None:
        employer_outcome, employer_missing = "unknown", "desired_employer_type"
        employer_candidate = "chưa nêu nguyện vọng"
    elif facts.desired_employer_type == employer_type:
        employer_outcome, employer_missing = "match", None
        employer_candidate = "trùng nguyện vọng"
    else:
        employer_outcome, employer_missing = "different", None
        employer_candidate = (
            f"mong muốn {catalog.EMPLOYER_TYPE_LABELS.get(facts.desired_employer_type)}"
        )
    rows.append(
        SoftRow(
            key="employer_type",
            label="Loại hình cơ sở",
            requirement_text=f"loại hình {catalog.EMPLOYER_TYPE_LABELS.get(employer_type, employer_type)}",
            candidate_text=employer_candidate,
            outcome=employer_outcome,
            points=weights.points("employer_type", employer_outcome),
            max_points=weights.max_points("employer_type"),
            missing_field=employer_missing,
        )
    )

    # 3. Lương
    offer = reference.get("salary_max") or reference.get("salary_min")
    expectation = facts.salary_expectation_jpy
    numerator, denominator = weights.salary_near_ratio
    if expectation is None or offer is None:
        salary_outcome = "unknown"
        salary_missing = "salary_expectation_jpy" if expectation is None else None
        salary_candidate = "chưa nêu mức mong muốn" if expectation is None else f"kỳ vọng {format_thousand(expectation)} ¥"
    else:
        salary_missing = None
        salary_candidate = f"kỳ vọng {format_thousand(expectation)} ¥"
        if offer >= expectation:
            salary_outcome = "meets"
        elif offer * denominator >= expectation * numerator:
            # Phép nhân số nguyên thay cho phép chia số thực: kết quả không phụ
            # thuộc sai số dấu phẩy động, nên chạy lại bao nhiêu lần cũng như nhau.
            salary_outcome = "near"
        else:
            salary_outcome = "below"
    rows.append(
        SoftRow(
            key="salary",
            label="Lương",
            requirement_text=(
                f"lương {format_thousand(offer)} ¥" if offer else "chưa công bố lương"
            ),
            candidate_text=salary_candidate,
            outcome=salary_outcome,
            points=weights.points("salary", salary_outcome),
            max_points=weights.max_points("salary"),
            missing_field=salary_missing,
        )
    )

    # 4. Chi phí
    cost = reference.get("cost_total_vnd")
    budget = facts.budget_vnd
    if cost is None or budget is None:
        cost_outcome = "unknown"
        cost_missing = "budget_vnd" if budget is None else None
        cost_candidate = "chưa rõ khả năng" if budget is None else f"khả năng {format_thousand(budget)} đ"
    else:
        cost_missing = None
        cost_candidate = f"khả năng {format_thousand(budget)} đ"
        cost_outcome = "within" if cost <= budget else "over"
    rows.append(
        SoftRow(
            key="cost",
            label="Chi phí",
            requirement_text=(
                f"chi phí {format_thousand(cost)} đ" if cost else "chưa rõ chi phí"
            ),
            candidate_text=cost_candidate,
            outcome=cost_outcome,
            points=weights.points("cost", cost_outcome),
            max_points=weights.max_points("cost"),
            missing_field=cost_missing,
        )
    )

    return rows


# --- Sinh câu giải thích bằng mã, không dùng mô hình ngôn ngữ ---


def build_gaps(
    hard_rows: Sequence[CriterionRow],
    soft_rows: Sequence[SoftRow],
) -> tuple[str, ...]:
    gaps: list[str] = []
    for row in hard_rows:
        if row.result == KHONG_DAT:
            gaps.append(f"{row.label}: đơn {row.requirement_text}, {row.candidate_text}.")
    for row in soft_rows:
        if row.points == 0 and row.outcome not in ("unknown",):
            gaps.append(f"{row.label}: {row.requirement_text}, {row.candidate_text}.")
    return tuple(gaps)


def collect_missing(
    hard_rows: Sequence[CriterionRow],
    soft_rows: Sequence[SoftRow],
) -> tuple[str, ...]:
    keys = {row.missing_field for row in hard_rows if row.missing_field}
    keys |= {row.missing_field for row in soft_rows if row.missing_field}
    return tuple(MISSING_PROMPTS[key] for key in MISSING_ORDER if key in keys)


def _labels_for(order: dict[str, Any]) -> dict[str, str | None]:
    requirements = order.get("requirements") or {}
    education = requirements.get("education_required")
    return {
        "employer_type": catalog.EMPLOYER_TYPE_LABELS.get(order.get("employer_type", "")),
        "program": catalog.PROGRAM_LABELS.get(order.get("program", "")),
        "region_group": catalog.REGION_LABELS.get(order.get("region_group") or ""),
        "japanese_required": catalog.JAPANESE_LEVEL_LABELS.get(
            requirements.get("japanese_required", "")
        ),
        "education_required": catalog.EDUCATION_LABELS.get(education) if education else None,
    }


# --- Đối chiếu toàn danh mục ---


def match_orders(
    orders: Sequence[dict[str, Any]],
    facts: CandidateFacts,
    *,
    weights: Weights,
    as_of: date,
) -> MatchResult:
    eligible_items: list[MatchItem] = []
    rejected_items: list[MatchItem] = []

    for order in orders:
        hard_rows = tuple(evaluate_hard(order, facts, as_of))
        eligible = is_eligible(hard_rows)

        # Đơn bị loại không được chấm điểm. Hiện "45/100" cạnh dòng "KHÔNG ĐẠT"
        # là mời người đọc đem so sánh hai thứ không so sánh được với nhau.
        soft_rows = tuple(evaluate_soft(order, facts, weights)) if eligible else ()
        score = sum(row.points for row in soft_rows)

        item = MatchItem(
            code=order.get("code", ""),
            title=order.get("title", ""),
            employer_name=order.get("employer_name", ""),
            prefecture=order.get("prefecture", ""),
            region_group=order.get("region_group"),
            employer_type=order.get("employer_type", ""),
            program=order.get("program", ""),
            deadline=str(order.get("deadline", "")),
            eligible=eligible,
            score=score,
            rank=None,
            hard_rows=hard_rows,
            soft_rows=soft_rows,
            gaps=build_gaps(hard_rows, soft_rows),
            missing_info=collect_missing(hard_rows, soft_rows),
            labels=_labels_for(order),
        )
        (eligible_items if eligible else rejected_items).append(item)

    # Điểm cao lên trước. Hòa điểm thì đơn sắp hết hạn lên trước, vì đó là cơ hội
    # ứng viên sẽ mất trước tiên. Hòa nốt thì theo mã đơn, để thứ tự không phụ
    # thuộc vào thứ tự MongoDB trả về.
    eligible_items.sort(key=lambda item: (-item.score, item.deadline, item.code))
    rejected_items.sort(key=lambda item: (item.deadline, item.code))

    ranked = tuple(
        MatchItem(**{**item.__dict__, "rank": index})
        for index, item in enumerate(eligible_items, start=1)
    )
    items = ranked + tuple(rejected_items)

    seen: list[str] = []
    for item in items:
        for prompt in item.missing_info:
            if prompt not in seen:
                seen.append(prompt)
    ordered_missing = tuple(
        prompt for key in MISSING_ORDER
        for prompt in (MISSING_PROMPTS[key],)
        if prompt in seen
    )

    return MatchResult(
        as_of=as_of.isoformat(),
        engine_version=ENGINE_VERSION,
        weights_version=weights.version,
        weights_fingerprint=weights.fingerprint,
        profile_code=facts.profile_code,
        profile_version=facts.profile_version,
        total_considered=len(items),
        eligible_count=len(ranked),
        items=items,
        missing_info=ordered_missing,
    )
