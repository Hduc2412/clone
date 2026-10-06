"""Bốn nhánh của phòng tư vấn theo đơn.

Khách đang xem một đơn cụ thể và hỏi *"tôi có hợp đơn này không"*. Module này
nhận kết quả đối chiếu đúng đơn ấy rồi phân ra bốn nhánh của sơ đồ nghiệp vụ, và
dựng khối chữ tất định mà lớp diễn đạt được phép nói lại.

## Vì sao phân nhánh ở đây chứ không để mô hình tự quyết

Nhánh nào là một **kết luận nghiệp vụ**: đạt hay chưa đạt, còn thiếu gì, có nên
mời học không. Để mô hình ngôn ngữ tự chọn thì cùng một hồ sơ có thể ra hai kết
luận khác nhau ở hai lần hỏi, và không ai giải trình được vì sao. Ở đây nhánh
suy trực tiếp từ các dòng tiêu chí do bộ đối chiếu chấm — thuần, tất định.

## Thứ tự ưu tiên của nhánh, và lý do

Hỏi trước, kết luận sau. Nếu còn tiêu chí bắt buộc chưa rõ thì **chưa được** nói
"bạn chưa phù hợp" — vì có thể chỉ là chưa hỏi tới. Đây chính là quy tắc "chỉ
loại khi chắc chắn" của bộ đối chiếu, áp lên tầng hội thoại.

Ngoại lệ: nếu đã có tiêu chí **chắc chắn không đạt** thì nói ngay, kể cả khi còn
ô chưa rõ. Bắt một người quá tuổi khai thêm bằng cấp rồi mới báo trượt là làm
mất thời gian của họ.

## Mời học chỉ khi tiếng Nhật là thứ chặn đường

Đây là chỗ dễ làm ẩu nhất. Thấy "chưa phù hợp" rồi mời học tiếng là sai khi
người ta trượt vì quá tuổi hoặc vì đơn chỉ tuyển nữ — học xong vẫn không đi được,
và lời mời ấy thành ra bán khóa học cho người không có cửa.

Nên lộ trình học chỉ dựng khi **tiếng Nhật nằm trong lý do chặn**, và những lý do
chặn khác được nói thẳng là không học được để bù.
"""
from dataclasses import dataclass, field
from typing import Any, Sequence

from app.consultation import eligibility
from app.learning import path as learning_path
from app.matching import engine as engine_mod
from app.matching.engine import CHUA_RO, DAT, KHONG_DAT, MISSING_PROMPTS, MatchItem


# Ba nhánh kết luận. Nhánh thứ tư của sơ đồ — "khách chọn đơn khác" — không sinh
# từ dữ liệu mà do khách bấm, nên không nằm ở đây.
THIEU_THONG_TIN = "thieu_thong_tin"
PHU_HOP = "phu_hop"
CHUA_PHU_HOP = "chua_phu_hop"

# Tiêu chí tiếng Nhật trong bảng điều kiện bắt buộc.
KHOA_TIENG_NHAT = "japanese"

# Hỏi tối đa hai câu một lượt. Hỏi dồn năm câu thì người ta bỏ giữa chừng.
TOI_DA_CAU_HOI = 2


@dataclass(frozen=True)
class Advice:
    """Kết luận cho một đơn, kèm mọi thứ cần để dựng câu trả lời."""

    branch: str
    order_code: str
    order_title: str
    eligible: bool
    score: int
    #: Dòng tiêu chí chắc chắn không đạt — lý do thật sự chặn đường.
    blockers: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    #: Dòng tiêu chí chưa rõ vì hồ sơ chưa khai.
    unknowns: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    #: Dòng tiêu chí đã đạt — phần đưa ra để khách biết mình mạnh ở đâu.
    strengths: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    questions: tuple[str, ...] = field(default_factory=tuple)
    learning: learning_path.LearningPath | None = None
    #: Vì sao không có lộ trình học. Rỗng khi có, hoặc khi không cần.
    learning_note: str = ""
    #: Ứng viên đã xem lại và xác nhận hồ sơ chưa.
    profile_confirmed: bool = True
    #: Điểm phù hợp đã có nghĩa để hiển thị chưa.
    #
    #: Chưa nêu nguyện vọng nào thì cả bốn dòng mềm đều chưa rõ và tổng điểm
    #: xuống gần 0 — màn hình hiện "5/100" cạnh "đạt các điều kiện bắt buộc",
    #: một cặp câu nói điều sai. Xem `engine.xep_hang_duoc`.
    score_ranked: bool = True
    #: Khối chữ tất định. Lớp diễn đạt chỉ được nói lại những gì nằm trong đây.
    block: str = ""

    @property
    def can_register(self) -> bool:
        """Ba điều kiện, và điều kiện thứ ba hay bị bỏ quên.

        Phòng tư vấn cho phép đối chiếu ngay trên hồ sơ máy vừa đọc từ CV, chưa
        cần ứng viên xác nhận — vì câu hỏi ở đây hẹp ("tôi có hợp đơn này
        không") và họ đang ngồi xem trực tiếp.

        Nhưng **đăng ký** thì vẫn đòi hồ sơ đã xác nhận. Máy có thể đọc nhầm
        "N4" thành "N3"; tạo một hồ sơ đăng ký từ chỗ đọc nhầm ấy là đẩy cái sai
        sang cho nhân viên gọi điện. Đây chính là chốt chặn "không tạo đăng ký
        từ suy đoán của máy", giữ nguyên chứ không nới.
        """
        return self.branch == PHU_HOP and self.eligible and self.profile_confirmed


def _rows(item: MatchItem, ket_qua: str) -> tuple[dict[str, Any], ...]:
    return tuple(row.as_dict() for row in item.hard_rows if row.result == ket_qua)


def _cau_hoi(unknowns: Sequence[dict[str, Any]]) -> tuple[str, ...]:
    """Câu hỏi bổ sung, lấy từ đúng bộ câu của bộ đối chiếu.

    Dùng lại `MISSING_PROMPTS` thay vì tự viết câu mới: một nguồn duy nhất thì
    sửa cách hỏi ở một chỗ là cả hệ thống đổi theo, và câu hỏi luôn khớp với
    trường mà bộ đối chiếu thật sự cần.
    """
    cau: list[str] = []
    for row in unknowns:
        truong = row.get("missing_field")
        loi = MISSING_PROMPTS.get(truong or "")
        if loi and loi not in cau:
            cau.append(loi)
        if len(cau) >= TOI_DA_CAU_HOI:
            break
    return tuple(cau)


def _lo_trinh(
    *,
    blockers: Sequence[dict[str, Any]],
    required_japanese: str | None,
    profile_level: str | None,
    courses: Sequence[dict[str, Any]],
) -> tuple[learning_path.LearningPath | None, str]:
    """Lộ trình học, chỉ khi tiếng Nhật là thứ chặn đường.

    Trả về `(lộ trình, ghi chú)`. Ghi chú nói vì sao không có lộ trình, để câu
    trả lời giải thích được thay vì im lặng bỏ qua.
    """
    chan_vi_tieng_nhat = any(row.get("key") == KHOA_TIENG_NHAT for row in blockers)
    if not chan_vi_tieng_nhat:
        return None, ""

    khac = [row for row in blockers if row.get("key") != KHOA_TIENG_NHAT]
    if khac:
        # Học xong vẫn không đi được. Nói thẳng còn hơn mời học rồi để họ phát
        # hiện ra sau khi đã đóng tiền.
        ten = ", ".join(str(row.get("label") or row.get("key")) for row in khac)
        return None, (
            f"Ngoài tiếng Nhật, hồ sơ còn chưa đạt ở: {ten}. "
            "Học thêm tiếng Nhật không bù được những mục này."
        )

    can = required_japanese
    if not profile_level:
        return None, "Chưa biết trình độ tiếng Nhật hiện tại nên chưa tính được lộ trình."
    if not can:
        return None, "Đơn không ghi rõ trình độ tiếng Nhật yêu cầu."

    lo_trinh = learning_path.build(courses, level_from=profile_level, level_to=can)
    if lo_trinh is None:
        return None, (
            f"Danh mục khóa học hiện chưa có khóa nào nối từ "
            f"{learning_path.label(profile_level)} lên {learning_path.label(can)}. "
            "Nhân viên tư vấn sẽ trao đổi phương án học phù hợp."
        )
    return lo_trinh, ""


def _tien(so: int | None) -> str:
    if not so:
        return ""
    return f"{so:,}đ".replace(",", ".")


def render_block(advice: "Advice") -> str:
    """Khối chữ tất định — nguồn duy nhất mà lớp diễn đạt được đọc.

    Mọi con số xuất hiện trong câu trả lời cuối cùng phải có mặt ở đây. Chốt
    chặn hậu kiểm dựa vào đúng điều đó để loại câu có số lạ.
    """
    dong: list[str] = [
        f"ĐƠN ĐANG XÉT: {advice.order_code} — {advice.order_title}",
        f"KẾT LUẬN: {_NHAN_NHANH[advice.branch]}",
    ]
    if advice.branch == PHU_HOP:
        dong.append(f"ĐIỂM PHÙ HỢP VỚI NGUYỆN VỌNG: {advice.score}/100")

    if advice.strengths:
        dong.append("")
        dong.append("ĐÃ ĐẠT:")
        dong += [
            f"- {row['label']}: {row['requirement_text']} — {row['candidate_text']}"
            for row in advice.strengths
        ]
    if advice.blockers:
        dong.append("")
        dong.append("CHƯA ĐẠT:")
        dong += [
            f"- {row['label']}: {row['requirement_text']} — {row['candidate_text']}"
            for row in advice.blockers
        ]
    if advice.unknowns:
        dong.append("")
        dong.append("CHƯA RÕ (hồ sơ chưa khai, KHÔNG phải là không đạt):")
        dong += [
            f"- {row['label']}: {row['requirement_text']} — {row['candidate_text']}"
            for row in advice.unknowns
        ]
    if advice.questions:
        dong.append("")
        dong.append("CẦN HỎI THÊM:")
        dong += [f"- {cau}" for cau in advice.questions]

    if advice.learning is not None:
        lo = advice.learning
        dong.append("")
        dong.append("LỘ TRÌNH HỌC ĐỂ ĐỦ ĐIỀU KIỆN:")
        dong.append(
            f"- Từ {learning_path.label(lo.level_from)} lên "
            f"{learning_path.label(lo.level_to)}: {lo.months_text}"
        )
        for khoa in lo.courses:
            dong.append(f"- Khóa: {khoa.get('title')} ({khoa.get('code')})")
        if lo.tuition_incomplete:
            dong.append("- Học phí: chưa có đủ thông tin, nhân viên sẽ báo lại")
        elif lo.tuition_vnd:
            if lo.package_total_vnd:
                # Hai con số và quan hệ giữa chúng phải nằm **trên cùng một
                # dòng**. Bắt buộc nêu tổng — nói học phí trơ trọi là để khách
                # hiểu sai số tiền phải chuẩn bị cho cả chương trình.
                #
                # Viết liền một dòng còn vì lý do thứ hai: chốt hậu kiểm của bot
                # chỉ cho phép nói "A nằm trong B" khi có một dòng nguồn chứa cả
                # hai con số. Tách làm hai dòng thì chính câu đúng cũng bị loại.
                dong.append(
                    f"- Học phí {_tien(lo.tuition_vnd)}, là một chặng trong tổng "
                    f"chi phí chương trình {_tien(lo.package_total_vnd)}"
                )
            else:
                dong.append(f"- Học phí: {_tien(lo.tuition_vnd)}")
    elif advice.learning_note:
        dong.append("")
        dong.append(f"VỀ VIỆC HỌC THÊM: {advice.learning_note}")

    # Nêu điều kiện sức khỏe ở những nhánh khách còn đi tiếp được — tức là
    # **trước khi họ đóng đồng nào**. Trước đây họ chỉ biết sau khi đặt cọc 10
    # triệu rồi đi khám.
    #
    # Không nêu ở nhánh đã chắc chắn trượt vì lý do khác: người quá tuổi không
    # cần nghe thêm một điều kiện nữa, nghe chỉ thấy bị dồn.
    if advice.branch != CHUA_PHU_HOP or advice.learning is not None:
        dong.append("")
        dong.append(eligibility.render_suc_khoe())

    return "\n".join(dong)


_NHAN_NHANH = {
    THIEU_THONG_TIN: "chưa đủ thông tin để kết luận",
    PHU_HOP: "đạt các điều kiện bắt buộc",
    CHUA_PHU_HOP: "chưa đạt điều kiện bắt buộc",
}


def build(
    item: MatchItem,
    *,
    required_japanese: str | None,
    profile_level: str | None,
    courses: Sequence[dict[str, Any]] = (),
    profile_confirmed: bool = True,
) -> Advice:
    """Phân nhánh và dựng khối chữ. Thuần — không chạm database, không gọi mô hình."""
    blockers = _rows(item, KHONG_DAT)
    unknowns = _rows(item, CHUA_RO)
    strengths = _rows(item, DAT)

    if blockers:
        branch = CHUA_PHU_HOP
    elif unknowns:
        branch = THIEU_THONG_TIN
    else:
        branch = PHU_HOP

    lo_trinh, ghi_chu = _lo_trinh(
        blockers=blockers,
        required_japanese=required_japanese,
        profile_level=profile_level,
        courses=courses,
    )

    advice = Advice(
        branch=branch,
        order_code=item.code,
        order_title=item.title,
        eligible=item.eligible,
        score=item.score,
        blockers=blockers,
        unknowns=unknowns,
        strengths=strengths,
        questions=_cau_hoi(unknowns),
        learning=lo_trinh,
        learning_note=ghi_chu,
        profile_confirmed=profile_confirmed,
        score_ranked=engine_mod.xep_hang_duoc(item.soft_rows),
    )
    # `block` không tự tính được trong `__init__` vì dataclass đóng băng, nên
    # dựng xong rồi thay — vẫn là một đối tượng bất biến với nơi gọi.
    return Advice(**{**advice.__dict__, "block": render_block(advice)})


def as_dict(advice: Advice) -> dict[str, Any]:
    """Hình dạng trả cho giao diện. Không kèm `block` — đó là thứ của lớp diễn đạt."""
    lo = advice.learning
    return {
        "branch": advice.branch,
        "branch_label": _NHAN_NHANH[advice.branch],
        "order_code": advice.order_code,
        "order_title": advice.order_title,
        "eligible": advice.eligible,
        "score": advice.score,
        "can_register": advice.can_register,
        "profile_confirmed": advice.profile_confirmed,
        "score_ranked": advice.score_ranked,
        "blockers": list(advice.blockers),
        "unknowns": list(advice.unknowns),
        "strengths": list(advice.strengths),
        "questions": list(advice.questions),
        "learning": None
        if lo is None
        else {
            "level_from": lo.level_from,
            "level_from_label": learning_path.label(lo.level_from),
            "level_to": lo.level_to,
            "level_to_label": learning_path.label(lo.level_to),
            "months_text": lo.months_text,
            "tuition_vnd": lo.tuition_vnd,
            "tuition_incomplete": lo.tuition_incomplete,
            "package_total_vnd": lo.package_total_vnd,
            "courses": [
                {"code": k.get("code"), "title": k.get("title"), "format": k.get("format")}
                for k in lo.courses
            ],
        },
        "learning_note": advice.learning_note,
    }
