"""Tóm tắt tự động khi dịch vụ mô hình không trả lời — dựng bằng quy tắc.

## Vì sao không chỉ báo "trợ lý đang bận"

Ngày 06/10, khách hỏi *"tôi còn thiếu gì để nộp đơn này"* đúng lúc model chính
quá thời gian chờ và model dự phòng báo 503. Câu nhận được là "phần trợ lý tư vấn
đang bận". Trong khi đó câu trả lời đã nằm sẵn trong kết quả đối chiếu: tiêu chí
nào chưa đạt, mục nào hồ sơ chưa khai, đơn nào khác hồ sơ đạt điều kiện.

## Ba điều bản tóm tắt này KHÔNG làm

- **Không giả làm lời tư vấn.** Câu mở đầu nói thẳng đây là tóm tắt tự động lúc
  trợ lý chưa trả lời được; nguồn của lượt vẫn ghi là `khong_goi_duoc`, nên số liệu
  "bot không đoán" không tự đẹp lên lúc dịch vụ chết.
- **Không đoán câu hỏi.** Không có mô hình thì không hiểu được câu hỏi tự nhiên —
  dò từ khóa để giả vờ hiểu là trả lời sai câu một cách tự tin. Nên bản tóm tắt
  giống nhau với mọi câu hỏi: nó là thứ chắc chắn đúng về hồ sơ, không phải câu
  trả lời cho đúng câu vừa hỏi. Câu hỏi của khách vẫn được lưu nguyên.
- **Không thêm gì ngoài dữ liệu.** Mọi chữ ở đây lấy từ kết quả đối chiếu.
"""
from typing import Any, Sequence

from app.consultation import advice as advice_mod
from app.consultation import khoi_mo_rong
from app.learning import path as learning_path

MO_DAU = (
    "Trợ lý tư vấn đang tạm thời chưa trả lời được, nên mình gửi bạn tóm tắt tự động "
    "từ kết quả đối chiếu — đây chưa phải câu trả lời riêng cho câu bạn vừa hỏi."
)
KET = (
    "Bạn hỏi lại sau ít phút để được tư vấn kỹ hơn, hoặc để lại tin nhắn cho nhân viên "
    "tư vấn nhé."
)

_KET_LUAN = {
    advice_mod.PHU_HOP: "hồ sơ đạt các điều kiện bắt buộc của đơn này",
    advice_mod.CHUA_PHU_HOP: "hồ sơ chưa đạt điều kiện bắt buộc của đơn này",
    advice_mod.THIEU_THONG_TIN: "chưa đủ thông tin để kết luận về đơn này",
}


def _muc(rows: Sequence[dict[str, Any]]) -> str:
    # Cùng khuôn với `advice.render_block`: `requirement_text` đã mang sẵn chữ
    # "yêu cầu…", thêm tiền tố nữa là thành "đơn yêu cầu yêu cầu N4".
    return "; ".join(
        f"{r.get('label')} ({r.get('requirement_text')} — {r.get('candidate_text')})"
        for r in rows
    )


def _don_dat(log: dict[str, Any] | None, *, tru_ma: str | None, toi_da: int = 3) -> list[str]:
    if not log:
        return []
    return [
        f"{r.get('code')} ({r.get('title')})"
        for r in log.get("items") or ()
        if r.get("eligible") and r.get("code") != tru_ma
    ][:toi_da]


def theo_don(
    ket_qua: "advice_mod.Advice", *, log_ca_danh_muc: dict[str, Any] | None = None
) -> str:
    """Tóm tắt cho phòng tư vấn theo đơn."""
    cau = [MO_DAU, f"Với đơn {ket_qua.order_code}, {_KET_LUAN.get(ket_qua.branch, '')}."]
    if ket_qua.blockers:
        cau.append(f"Chưa đạt: {_muc(ket_qua.blockers)}.")
    if ket_qua.unknowns:
        cau.append(
            f"Chưa rõ vì hồ sơ chưa khai — chưa phải là không đạt: {_muc(ket_qua.unknowns)}."
        )
    if ket_qua.learning is not None:
        lo = ket_qua.learning
        khoa = ", ".join(f"{k.get('title')} ({k.get('code')})" for k in lo.courses)
        cau.append(
            f"Danh mục của công ty có lộ trình từ {learning_path.label(lo.level_from)} lên "
            f"{learning_path.label(lo.level_to)} trong {lo.months_text}: {khoa}."
        )
    elif ket_qua.learning_note:
        cau.append(ket_qua.learning_note.rstrip(".") + ".")
    khac = _don_dat(log_ca_danh_muc, tru_ma=ket_qua.order_code)
    if khac and ket_qua.branch != advice_mod.PHU_HOP:
        cau.append(f"Các đơn khác hồ sơ đạt điều kiện bắt buộc: {', '.join(khac)}.")
    cau.append(KET)
    return " ".join(cau)


def theo_ho_so(
    log: dict[str, Any] | None,
    *,
    ho_so_da_xac_nhan: bool,
    con_thieu: Sequence[str] = (),
    khoa_hoc: Sequence[dict[str, Any]] = (),
    trinh_do: str | None = None,
) -> str:
    """Tóm tắt cho Agent cấp hồ sơ.

    `con_thieu` là **khóa trường** (`experience_years`…) — đổi sang nhãn ở đây. Kiểm
    trên trình duyệt 07/10: bản đầu in thẳng "Hồ sơ còn thiếu: experience_years,
    salary_expectation_jpy, budget_vnd".

    `khoa_hoc` và `trinh_do`: khi tiếng Nhật là chỗ vướng, nêu khóa trong danh mục
    nhận người ở đúng trình độ hiện tại. Kiểm cùng lượt: khách chưa học tiếng hỏi
    "nên làm gì", bản đầu không nhắc khóa nào dù danh mục có sẵn khóa từ chưa học.
    """
    cau = [MO_DAU]
    if log is None:
        cau.append(
            "Hồ sơ của bạn chưa được đối chiếu với các đơn."
            if ho_so_da_xac_nhan
            else "Hồ sơ của bạn chưa được xác nhận nên chưa đối chiếu với các đơn; "
            "bạn xác nhận hồ sơ để xem đơn phù hợp."
        )
    else:
        dat = [r for r in log.get("items") or () if r.get("eligible")]
        cau.append(
            f"Hệ thống đã xét {log.get('total_considered') or len(log.get('items') or ())} đơn, "
            f"hồ sơ đạt điều kiện bắt buộc ở {len(dat)} đơn."
        )
        if khac := _don_dat(log, tru_ma=None):
            cau.append(f"Một số đơn đạt: {', '.join(khac)}.")
        vuong = _tieu_chi_vuong_nhieu(log)
        if vuong:
            cau.append(f"Các đơn chưa đạt chủ yếu vướng ở: {vuong}.")
        if "Tiếng Nhật" in vuong and trinh_do:
            if hop := [k for k in khoa_hoc if k.get("level_from") == trinh_do]:
                cau.append(
                    "Danh mục của công ty có "
                    + "; ".join(
                        f"khóa {k.get('title')} ({k.get('code')}) nhận người "
                        f"{_tu_trinh_do(trinh_do)}, học tới {learning_path.label(k.get('level_to'))}"
                        for k in hop
                    )
                    + "."
                )
    if con_thieu:
        from app.consultation.context_builder import NHAN

        cau.append(f"Hồ sơ còn thiếu: {', '.join(NHAN.get(k, k) for k in con_thieu)}.")
    cau.append(KET)
    return " ".join(c for c in cau if c)


def _tu_trinh_do(trinh_do: str) -> str:
    """"chưa học" hoặc "từ N4" — đọc liền mạch sau chữ "nhận người"."""
    nhan = learning_path.label(trinh_do)
    return nhan[0].lower() + nhan[1:] if nhan.startswith("Chưa") else f"từ {nhan}"


def _tieu_chi_vuong_nhieu(log: dict[str, Any], toi_da: int = 3) -> str:
    _, dem = khoi_mo_rong.dem_tieu_chi_truot(log)
    return ", ".join(ten for ten, _ in dem.most_common(toi_da))
