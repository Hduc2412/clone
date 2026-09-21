"""Trọng số xếp hạng mềm, đọc từ file cấu hình.

Để trọng số ngoài mã nguồn vì hai lý do. Thứ nhất, doanh nghiệp có thể muốn đổi
mức ưu tiên giữa khu vực và lương mà không cần sửa code. Thứ hai, và quan trọng
hơn, khi bảo vệ mà hội đồng hỏi "vì sao đơn này xếp trên đơn kia" thì mở đúng một
file ra là trả lời được, thay vì đi tìm con số nằm rải trong mã nguồn.

Thiếu file thì **báo lỗi**, tuyệt đối không lặng lẽ quay về một bộ số cứng trong
code. Một bộ số dự phòng ẩn đâu đó chính là thứ phá vỡ tính giải trình được: kết
quả trông vẫn hợp lý nhưng không ai biết nó tính theo trọng số nào.
"""
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from app.core.config import settings


DEFAULT_WEIGHTS_PATH: Path = Path(__file__).with_name("weights.json")

# Bốn tiêu chí mềm, cộng lại đúng 100 điểm.
REQUIRED_CRITERIA: tuple[str, ...] = ("region", "employer_type", "salary", "cost")
TOTAL_POINTS = 100


class WeightsError(ValueError):
    """Cấu hình trọng số không hợp lệ. Thông báo viết bằng tiếng Việt cho người vận hành."""


@dataclass(frozen=True)
class Weights:
    version: str
    fingerprint: str
    weights: Mapping[str, int]
    rules: Mapping[str, Mapping[str, int]]
    params: Mapping[str, int]

    def points(self, criterion: str, outcome: str) -> int:
        try:
            return self.rules[criterion][outcome]
        except KeyError as exc:
            raise WeightsError(
                f"Không có luật '{outcome}' cho tiêu chí '{criterion}'."
            ) from exc

    def max_points(self, criterion: str) -> int:
        return self.weights[criterion]

    @property
    def salary_near_ratio(self) -> tuple[int, int]:
        return (
            self.params["salary_near_numerator"],
            self.params["salary_near_denominator"],
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "fingerprint": self.fingerprint,
            "weights": dict(self.weights),
            "rules": {key: dict(value) for key, value in self.rules.items()},
            "params": dict(self.params),
        }


def _require_int(value: Any, label: str) -> int:
    # Từ chối số thực có chủ ý: điểm là số nguyên thì tổng điểm luôn tái lập được
    # từng byte. Một trọng số 33.33 sẽ kéo theo sai số dấu phẩy động và làm hỏng
    # đúng cái tính chất khiến bộ đối chiếu này đáng tin.
    if isinstance(value, bool) or not isinstance(value, int):
        raise WeightsError(f"{label} phải là số nguyên, hiện là {value!r}.")
    if value < 0:
        raise WeightsError(f"{label} không được âm, hiện là {value}.")
    return value


def parse_weights(raw: dict[str, Any]) -> Weights:
    """Kiểm tra và dựng bộ trọng số. Hàm thuần, dùng trực tiếp trong kiểm thử."""
    weights_raw = raw.get("weights")
    rules_raw = raw.get("rules")
    params_raw = raw.get("params", {})
    if not isinstance(weights_raw, dict) or not isinstance(rules_raw, dict):
        raise WeightsError("Cấu hình phải có hai mục 'weights' và 'rules'.")

    missing = set(REQUIRED_CRITERIA) - set(weights_raw)
    extra = set(weights_raw) - set(REQUIRED_CRITERIA)
    if missing:
        raise WeightsError(f"Thiếu tiêu chí: {', '.join(sorted(missing))}.")
    if extra:
        raise WeightsError(f"Có tiêu chí lạ: {', '.join(sorted(extra))}.")

    weights = {
        criterion: _require_int(weights_raw[criterion], f"Trọng số '{criterion}'")
        for criterion in REQUIRED_CRITERIA
    }
    total = sum(weights.values())
    if total != TOTAL_POINTS:
        raise WeightsError(
            f"Tổng trọng số phải bằng {TOTAL_POINTS}, hiện là {total}."
        )

    rules: dict[str, Mapping[str, int]] = {}
    for criterion in REQUIRED_CRITERIA:
        criterion_rules = rules_raw.get(criterion)
        if not isinstance(criterion_rules, dict) or not criterion_rules:
            raise WeightsError(f"Thiếu bảng luật cho tiêu chí '{criterion}'.")
        parsed = {
            outcome: _require_int(value, f"Luật '{criterion}.{outcome}'")
            for outcome, value in criterion_rules.items()
        }
        highest = max(parsed.values())
        # Bắt lỗi gõ nhầm kiểu đặt trọng số 40 nhưng luật cao nhất lại là 35:
        # tiêu chí đó sẽ không bao giờ đạt điểm tối đa mà không ai nhận ra.
        if highest != weights[criterion]:
            raise WeightsError(
                f"Tiêu chí '{criterion}' có trọng số {weights[criterion]} "
                f"nhưng luật cao nhất chỉ {highest}. Hai số này phải bằng nhau."
            )
        rules[criterion] = MappingProxyType(parsed)

    params = {
        key: _require_int(value, f"Tham số '{key}'")
        for key, value in params_raw.items()
    }
    numerator = params.get("salary_near_numerator")
    denominator = params.get("salary_near_denominator")
    if not denominator or numerator is None or not 0 < numerator <= denominator:
        raise WeightsError(
            "Tham số 'salary_near_numerator' phải lớn hơn 0 và không vượt "
            "'salary_near_denominator'."
        )

    canonical = json.dumps(
        {"weights": weights, "rules": {k: dict(v) for k, v in rules.items()}, "params": params},
        sort_keys=True,
        ensure_ascii=False,
    )
    fingerprint = "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]

    return Weights(
        version=str(raw.get("version", "0")),
        fingerprint=fingerprint,
        weights=MappingProxyType(weights),
        rules=MappingProxyType(rules),
        params=MappingProxyType(params),
    )


# Khóa theo đường dẫn và thời điểm sửa file. Nhờ vậy sửa trọng số giữa buổi demo
# là có hiệu lực ngay, không phải khởi động lại, mà đường chạy thường vẫn dùng
# bản đã nạp sẵn.
_CACHE: dict[tuple[str, int], Weights] = {}


def load_weights(path: Path | None = None) -> Weights:
    resolved = Path(path or settings.matching_weights_path or DEFAULT_WEIGHTS_PATH)
    if not resolved.exists():
        raise WeightsError(
            f"Không tìm thấy file trọng số: {resolved}. "
            "Hệ thống không dùng bộ số dự phòng vì kết quả xếp hạng phải giải trình được."
        )
    key = (str(resolved), resolved.stat().st_mtime_ns)
    cached = _CACHE.get(key)
    if cached is not None:
        return cached

    try:
        raw = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise WeightsError(f"File trọng số không phải JSON hợp lệ: {exc}.") from exc

    weights = parse_weights(raw)
    _CACHE.clear()
    _CACHE[key] = weights
    return weights


def clear_cache() -> None:
    _CACHE.clear()
