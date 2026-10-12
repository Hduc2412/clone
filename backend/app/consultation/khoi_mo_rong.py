"""Ba khối ngữ cảnh để trợ lý tư vấn **rộng hơn một đơn** — dựng bằng quy tắc.

## Vì sao có module này

Trước 07/10, phòng tư vấn theo đơn chỉ đọc bốn khối: hồ sơ, đơn đang xem, kết quả
đối chiếu với đơn ấy, điều kiện mức nền. Prompt lại dặn câu nào ngoài bốn khối thì
đáp "chưa có thông tin". Nên những câu khách hỏi nhiều nhất khi một đơn chưa được —
*"có đơn nào khác hợp với tôi không"*, *"tôi nên học gì"* — bị từ chối đúng theo
thiết kế, dù dữ liệu để trả lời đã nằm sẵn trong hệ thống: bộ đối chiếu đã chấm cả
danh mục, và bảng khóa học có nguồn cho từng ô.

Agent cấp hồ sơ thấy được năm đơn đạt, nhưng không thấy lý do các đơn còn lại trượt
và không thấy khóa học nào — nên câu *"chưa học tiếng thì nên làm gì"* cũng cụt.

## Ba nguyên tắc

1. **Đơn khác lấy từ kết quả của bộ đối chiếu**, không để mô hình tự chọn. Mô hình
   chỉ được giới thiệu đơn có trong khối này, và khối ghi rõ đơn nào đạt điều kiện
   bắt buộc theo nhật ký nào.
2. **Chưa xếp hạng được thì không nói thứ hạng.** Chưa có nguyện vọng nào thì điểm
   mềm vô nghĩa (`engine.xep_hang_duoc`); khối nói thẳng điều đó, và không in điểm.
3. **Khóa học chỉ là khóa trong danh mục đã công bố**, mỗi ô kèm nguồn. Danh mục
   rỗng thì khối nói rỗng — không có chỗ nào cho mô hình điền một khóa nó tự nghĩ.

Mọi con số in ra ở đây đều nằm trong khối cho phép của chốt hậu kiểm, nên mô hình
nhắc lại được — và chỉ những con số này.
"""
from collections import Counter
from typing import Any, Sequence

from app.learning import path as learning_path
from app.matching import engine

# Số đơn khác tối đa đưa vào. Đủ để có lựa chọn; ít đủ để prompt không phình theo
# danh mục — danh mục hai trăm đơn thì vẫn chỉ ba dòng.
SO_DON_KHAC = 3
# Số khóa tối đa. Danh mục hiện có một khóa; trần này giữ prompt gọn khi nó lớn lên.
SO_KHOA_TOI_DA = 5

_NGUON_O = {
    "kho_tri_thuc": "theo trang thông tin của công ty",
    "chu_dau_tu": "do công ty xác nhận, chưa có tài liệu công khai ghi",
}


def _xep_hang_duoc(row: dict[str, Any]) -> bool:
    """Cùng quy tắc với bộ đối chiếu (`engine.xep_hang_duoc`), không chép lại."""
    return engine.xep_hang_duoc(
        tuple(engine.SoftRow.tu_ban_ghi(dong) for dong in row.get("soft_rows") or ())
    )


def render_don_khac(
    log: dict[str, Any] | None,
    *,
    tru_ma: str | None = None,
    ho_so_da_xac_nhan: bool = True,
) -> str:
    """Các đơn khác hồ sơ đạt điều kiện bắt buộc, theo lần đối chiếu cả danh mục.

    `log` phải là nhật ký **cả danh mục** (`recommendation_logs.latest_for_profile`
    hoặc `run_matching` không `chi_don`). Nhật ký một đơn không nói gì về đơn khác.
    """
    dau = "[Các đơn khác đang tuyển — theo kết quả của bộ đối chiếu]"
    if not ho_so_da_xac_nhan:
        return (
            f"{dau}\nHồ sơ chưa được ứng viên xác nhận nên chưa đối chiếu với cả danh "
            "mục. Muốn biết đơn khác, ứng viên cần xác nhận hồ sơ trước."
        )
    if log is None:
        return f"{dau}\nChưa có lần đối chiếu nào với cả danh mục."

    dat = [r for r in log.get("items") or () if r.get("eligible") and r.get("code") != tru_ma]
    dong = [
        dau,
        f"Đã xét {log.get('total_considered') or len(log.get('items') or ())} đơn; "
        f"ngoài đơn đang xem, hồ sơ đạt điều kiện bắt buộc ở {len(dat)} đơn.",
    ]
    if not dat:
        dong.append("Không có đơn nào khác hồ sơ đạt điều kiện bắt buộc ở lần đối chiếu này.")
        return "\n".join(dong)

    co_hang = any(_xep_hang_duoc(r) for r in dat)
    if co_hang:
        dong.append(
            "Xếp theo điểm nguyện vọng của ứng viên (khu vực, loại cơ sở, lương, chi phí). "
            "Điểm này chỉ để xếp thứ tự, KHÔNG phải khả năng trúng tuyển."
        )
    else:
        dong.append(
            "Ứng viên chưa nêu nguyện vọng nên các đơn dưới đây CHƯA được xếp theo mức "
            "phù hợp — thứ tự không có nghĩa đơn nào hợp hơn. Không được nói đơn nào "
            "\"phù hợp nhất\"."
        )
    for r in dat[:SO_DON_KHAC]:
        nhan = r.get("labels") or {}
        manh = [
            f"- {r.get('code')} — {r.get('title')}",
            str(r.get("prefecture") or ""),
            str(nhan.get("employer_type") or r.get("employer_type") or ""),
            f"hạn nộp {r.get('deadline')}" if r.get("deadline") else "",
        ]
        if co_hang and _xep_hang_duoc(r):
            manh.append(f"điểm nguyện vọng {r.get('score')}/100")
        dong.append(" · ".join(m for m in manh if m))
    if len(dat) > SO_DON_KHAC:
        dong.append(f"(còn {len(dat) - SO_DON_KHAC} đơn đạt khác trên trang kết quả)")
    return "\n".join(dong)


def dem_tieu_chi_truot(log: dict[str, Any]) -> tuple[int, Counter[str]]:
    """`(số đơn chưa đạt, số đơn vướng ở từng tiêu chí)` của một nhật ký cả danh mục."""
    dem: Counter[str] = Counter()
    so_loai = 0
    for r in log.get("items") or ():
        if r.get("eligible"):
            continue
        so_loai += 1
        for dong in r.get("hard_rows") or ():
            if dong.get("result") == engine.KHONG_DAT:
                dem[str(dong.get("label") or dong.get("key"))] += 1
    return so_loai, dem


def render_ly_do_truot(log: dict[str, Any] | None) -> str:
    """Các đơn chưa đạt trượt ở tiêu chí nào — đếm theo tiêu chí, không liệt kê đơn.

    Trả lời được câu "tôi vướng chủ yếu ở đâu" mà không kéo cả bảng tiêu chí của
    mười mấy đơn vào prompt.
    """
    if log is None:
        return ""
    so_loai, dem = dem_tieu_chi_truot(log)
    if not so_loai:
        return ""
    dong = [
        "[Các đơn hồ sơ CHƯA đạt — vướng ở tiêu chí nào]",
        f"{so_loai} đơn chưa đạt điều kiện bắt buộc. Số đơn vướng ở từng tiêu chí "
        "(một đơn có thể vướng nhiều tiêu chí):",
    ]
    dong += [f"- {ten}: {so} đơn" for ten, so in sorted(dem.items(), key=lambda x: (-x[1], x[0]))]
    return "\n".join(dong)


def _thang(khoa: dict[str, Any]) -> str:
    lo, hi = khoa.get("months_min"), khoa.get("months_max")
    if lo and hi and hi != lo:
        return f"{lo}–{hi} tháng"
    if lo:
        return f"{lo} tháng"
    return ""


def _tien(so: int | None) -> str:
    return f"{so:,}đ".replace(",", ".") if so else ""


def render_khoa_hoc(courses: Sequence[dict[str, Any]]) -> str:
    """Khóa học tiếng Nhật **đã công bố** trong danh mục, mỗi ô kèm nguồn.

    Học phí và tổng gói nằm trên CÙNG một dòng — chốt hậu kiểm chỉ cho nói "A nằm
    trong B" khi có một dòng nguồn chứa cả hai (`qa._gop_hai_so_tien`).
    """
    dau = "[Khóa học tiếng Nhật trong danh mục của công ty]"
    if not courses:
        return (
            f"{dau}\nDanh mục hiện chưa có khóa nào được công bố. Không giới thiệu khóa "
            "cụ thể nào; nhân viên tư vấn sẽ trao đổi phương án học."
        )
    dong = [dau]
    for k in list(courses)[:SO_KHOA_TOI_DA]:
        nguon = k.get("source_fields") or {}
        manh = [
            f"- {k.get('title')} ({k.get('code')}): nhận từ "
            f"{learning_path.label(k.get('level_from'))}, học tới "
            f"{learning_path.label(k.get('level_to'))}"
        ]
        if nguon.get("level_to") in _NGUON_O:
            manh[0] += f" ({_NGUON_O[nguon['level_to']]})"
        if thang := _thang(k):
            manh.append(f"thời gian {thang}")
        if k.get("format"):
            manh.append(f"hình thức: {k['format']}")
        dong.append("; ".join(manh))
        if k.get("tuition_vnd") and k.get("package_total_vnd"):
            dong.append(
                f"  Học phí {_tien(k['tuition_vnd'])}, là một chặng trong tổng chi phí "
                f"chương trình {_tien(k['package_total_vnd'])}"
            )
        elif k.get("tuition_vnd"):
            dong.append(f"  Học phí {_tien(k['tuition_vnd'])}")
        else:
            dong.append("  Học phí: chưa có trong danh mục, nhân viên sẽ báo lại")
    dong.append(
        "Không có lịch khai giảng cụ thể trong danh mục. Học xong khóa không bảo đảm "
        "thi đỗ chứng chỉ hay trúng tuyển."
    )
    return "\n".join(dong)
