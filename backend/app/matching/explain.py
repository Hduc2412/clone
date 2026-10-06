"""Trình bày kết quả đối chiếu thành chữ, hoàn toàn bằng mã.

Module này **không import gì liên quan tới mô hình ngôn ngữ**, và có một ca kiểm
thử khẳng định điều đó. Lý do: mọi con số trong lời giải thích phải đã tồn tại
trong kết quả đối chiếu. Sau này nếu có cho mô hình diễn đạt lại cho mượt, thì
khối chữ sinh ở đây chính là thứ duy nhất nó được phép diễn đạt, và cũng là thước
đo để chặn nó thêm số liệu không có thật.

`render_block` in ra đúng định dạng trong `docs/design/11_KIEN_TRUC_TONG_QUAN.md`
mục 3.2. Định dạng đó có một đặc điểm dễ bỏ sót: **hai cột dùng chung một bề
rộng**, lấy theo chuỗi dài nhất của cả hai cột gộp lại. Căn theo từng cột riêng
sẽ ra một chuỗi khác.
"""
from typing import Sequence

from app.matching import catalog
from app.matching.engine import (
    CriterionRow,
    MatchItem,
    MatchResult,
    SoftRow,
    xep_hang_duoc,
)


# Hai tiêu chí này nói về **đơn hàng**, không phải về ứng viên: đơn còn tuyển
# không, còn hạn không. Chúng vẫn phải có trong bảng tiêu chí — đó là bằng chứng
# bộ lọc đã xét chúng. Nhưng đem vào câu "hồ sơ đạt các điều kiện bắt buộc" thì
# thành ra khen ứng viên vì đơn chưa hết hạn.
ORDER_LEVEL_KEYS = frozenset({"status", "deadline"})

# Luật mềm chấm điểm giữa cho trường chưa biết, để người khai thiếu không bị tụt
# hạng oan. Nhưng điểm ấy **không phải một lý do**: viết "xếp hạng 1 nhờ chi phí
# chưa rõ khả năng" là lấy cái chưa biết ra làm thành tích, và người đọc sẽ nghĩ
# hệ thống đang bịa.
NON_REASONS = frozenset({"unknown"})

HARD_TAG = "[cứng]"
SOFT_TAG = "[mềm]"
TAG_WIDTH = 6


def _outcome_text(row: CriterionRow | SoftRow) -> str:
    if isinstance(row, CriterionRow):
        return catalog.RESULT_LABELS.get(row.result, row.result)
    return f"+{row.points}"


def render_rows(rows: Sequence[CriterionRow | SoftRow]) -> list[str]:
    """Các dòng tiêu chí đã căn cột. In đúng những dòng được đưa vào, đúng thứ tự."""
    if not rows:
        return []
    width = max(
        len(text)
        for row in rows
        for text in (row.requirement_text, row.candidate_text)
    )
    lines: list[str] = []
    for row in rows:
        tag = HARD_TAG if row.kind == "cung" else SOFT_TAG
        lines.append(
            f"  {tag.ljust(TAG_WIDTH)} "
            f"{row.requirement_text.ljust(width)} · "
            f"{row.candidate_text.ljust(width)} → "
            f"{_outcome_text(row)}"
        )
    return lines


def render_block(item: MatchItem) -> str:
    """Khối lý do của một đơn hàng.

    Không lọc, không sắp xếp lại, không cắt bớt bên trong. In ra đúng những gì bộ
    đối chiếu đã sinh, nên nhìn khối này là thấy đúng thứ hệ thống đã cân nhắc.
    """
    header = f"đơn {item.code} · {item.employer_name} · {item.prefecture}"
    rows = [*item.hard_rows, *item.soft_rows]
    if not item.eligible:
        footer = "  → không đủ điều kiện"
    elif xep_hang_duoc(item.soft_rows):
        footer = f"  → tổng {item.score}/100 · hạng {item.rank}"
    else:
        # Chưa nêu nguyện vọng nào thì KHÔNG đưa điểm và hạng vào khối này.
        #
        # Khối này là **ngữ cảnh mô hình đọc**, và cũng là tập số mà chốt số so
        # vào. Để "tổng 5/100 · hạng 1" ở đây là hai cái sai cùng lúc: mô hình
        # được mời nhắc lại một thứ hạng chưa có nghĩa, và con số 5 trở thành số
        # hợp lệ để nó dùng ở bất cứ đâu trong câu trả lời.
        #
        # Điểm mềm đo mức khớp với nguyện vọng. Chưa có nguyện vọng thì nó đo
        # một thứ chưa tồn tại — xem `engine.xep_hang_duoc`.
        footer = "  → đạt điều kiện bắt buộc; chưa xếp hạng được vì chưa có nguyện vọng"
    return "\n".join([header, *render_rows(rows), footer])


def render_log_block(result: MatchResult, *, limit: int = 3) -> str:
    """Nhiều đơn liền nhau, ngăn bằng dòng trống. Dùng cho màn hình nhật ký."""
    blocks = [render_block(item) for item in result.items[:limit]]
    return "\n\n".join(blocks)


def render_template_text(item: MatchItem) -> str:
    """Hai đến bốn câu tiếng Việt, ghép từ chính dữ liệu của `item`.

    Mọi con số trong câu đều lấy từ `item`, không có con số nào được nghĩ ra thêm.
    """
    program = item.labels.get("program") or item.program
    employer = item.labels.get("employer_type") or item.employer_type
    sentences = [f"Đơn {item.code} – {item.title} tại {item.prefecture} ({employer}, {program})."]

    if item.eligible:
        passed = [
            f"{row.requirement_text} – {row.candidate_text}"
            for row in item.hard_rows
            if row.result == "DAT"
            and row.key not in ORDER_LEVEL_KEYS
            and "không" not in row.requirement_text[:7]
        ][:3]
        if passed:
            sentences.append(f"Hồ sơ đạt các điều kiện bắt buộc: {', '.join(passed)}.")

        scoring = [
            row
            for row in item.soft_rows
            if row.points > 0 and row.outcome not in NON_REASONS
        ][:2]
        if scoring:
            reasons = ", ".join(
                f"{row.label.lower()} {row.candidate_text}" for row in scoring
            )
            sentences.append(
                f"Xếp hạng {item.rank} với {item.score}/100 điểm nhờ {reasons}."
            )
        else:
            # Nhánh này kích hoạt **chính xác khi** không có dòng mềm nào được
            # cộng điểm, tức khi `xep_hang_duoc` là False.
            #
            # Bản trước nói "Xếp hạng 1 với 5/100 điểm." ngay tại đây. Ô điểm
            # trên màn hình đã được ẩn từ 05/10, nhưng câu này nằm **ngay bên
            # dưới ô đó** và vẫn nói ra đúng con số vừa ẩn — một bản sửa nửa
            # vời, và người đọc vẫn hiểu là "chỉ hợp 5 phần trăm".
            sentences.append(
                "Chưa xếp hạng được giữa các đơn vì bạn chưa nêu nguyện vọng "
                "(khu vực, loại cơ sở, lương, chi phí)."
            )
    elif item.gaps:
        sentences.append(f"Đơn này chưa phù hợp vì {item.gaps[0][0].lower()}{item.gaps[0][1:]}")
    else:
        sentences.append("Đơn này hiện không nhận hồ sơ.")

    if item.missing_info:
        sentences.append(f"Còn thiếu thông tin: {' '.join(item.missing_info)}")

    return " ".join(sentences)


def render_missing_info(result: MatchResult) -> str:
    """Danh sách câu hỏi cần hỏi thêm, gộp từ toàn bộ kết quả."""
    if not result.missing_info:
        return ""
    lines = [f"  • {prompt}" for prompt in result.missing_info]
    return "\n".join(["Để kết quả chính xác hơn, bạn cho biết thêm:", *lines])
