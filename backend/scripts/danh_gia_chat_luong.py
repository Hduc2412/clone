"""Đo chất lượng hệ thống theo `docs/design/07 §7`.

Đo hai hạng mục ngoại tuyến: phân loại ý định và trích số điện thoại. Cả hai là
mã thuần nên chạy được không cần mạng, không cần dịch vụ nào, và không cần cả
file `.env`.

**Ba câu hỏi của spec §4 do ba bộ khác trả lời**, không phải bộ này:

| Câu hỏi | Bộ trả lời |
|---|---|
| Trả lời sai khi thiếu căn cứ? | `scripts/nghiem_thu_chatbot.py` |
| Bộ lọc cứng có loại nhầm? | `tests/test_matching_seeded_data.py` (28 ca, chạy tự động) |
| Thông tin từ CV có đúng bản gốc? | `scripts/nghiem_thu_doc_cv.py` |

Phần đối chiếu từng nằm trong file này rồi bị gỡ: nó lặp lại thứ bộ kiểm thử đã
kiểm, mà một ca chạy tự động mỗi lần thì hơn hẳn một script phải nhớ chạy tay.

Chạy:  venv\\Scripts\\python.exe -m scripts.danh_gia_chat_luong
"""
import sys
import json
import os
from pathlib import Path

# Đặt trước mọi import từ `app`. `app.core.config` kiểm tra cấu hình ngay lúc
# import và chết nếu thiếu khóa, trong khi bộ đo này không gọi Gemini lần nào.
# Không có hai dòng dưới thì người vừa clone repo về chạy bộ đo sẽ nhận lỗi cấu
# hình, dù thứ nó đo chẳng liên quan gì tới khóa. Có `.env` thật thì `.env` thắng.
os.environ.setdefault("GEMINI_API_KEY", "danh-gia-khong-goi-mo-hinh-nen-khoa-gia")
os.environ.setdefault("JWT_SECRET", "danh-gia-khong-ky-token-nen-dung-khoa-gia-du-dai")

import app  # noqa: E402,F401  — đặt stdout về UTF-8 để in được tiếng Việt
from app.conversation.entity_extractor import extract_phone
from app.conversation.intent_classifier import classify


THU_MUC = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "danh_gia"


def doc(ten: str) -> dict:
    return json.loads((THU_MUC / ten).read_text(encoding="utf-8"))


def tieu_de(chu: str) -> None:
    print(f"\n{'─' * 76}\n{chu}\n{'─' * 76}")


# --- Câu 1 · Phân loại ý định -------------------------------------------------


def do_y_dinh() -> dict:
    du_lieu = doc("cau_hoi_y_dinh.json")
    sai = []
    for muc in du_lieu["cau_hoi"]:
        thuc_te = classify(muc["cau"])
        # Câu nằm giữa hai nhóm thì chấp nhận cả hai. Tính chúng là sai nghĩa là
        # đo tranh cãi về nhãn chứ không đo chất lượng bộ phân loại.
        chap_nhan = {muc["y_dinh"], *muc.get("y_dinh_chap_nhan_them", [])}
        if thuc_te not in chap_nhan:
            sai.append((muc["cau"], muc["y_dinh"], thuc_te, muc["do_kho"]))

    tong = len(du_lieu["cau_hoi"])
    dung = tong - len(sai)
    tieu_de(f"PHÂN LOẠI Ý ĐỊNH · {dung}/{tong} = {dung / tong:.1%} (mục tiêu ≥ 85%)")
    if sai:
        print(f"{len(sai)} câu sai:")
        for cau, mong, thuc, kho in sai[:15]:
            print(f"  [{kho}] {cau}")
            print(f"        mong đợi {mong} · nhận được {thuc}")
    return {"ten": "Phân loại ý định", "dat": dung, "tong": tong, "muc_tieu": 0.85}


# --- Câu 1b · Trích số điện thoại ---------------------------------------------


def do_so_dien_thoai() -> dict:
    du_lieu = doc("so_dien_thoai.json")
    sai = []
    for muc in du_lieu["cau_hoi"]:
        thuc_te = extract_phone(muc["cau"])
        if thuc_te != muc["so_mong_doi"]:
            sai.append((muc["cau"], muc["so_mong_doi"], thuc_te))

    tong = len(du_lieu["cau_hoi"])
    dung = tong - len(sai)
    tieu_de(f"TRÍCH SỐ ĐIỆN THOẠI · {dung}/{tong} = {dung / tong:.1%} (mục tiêu ≥ 95%)")
    if sai:
        print(f"{len(sai)} câu sai:")
        for cau, mong, thuc in sai:
            loai = "bắt nhầm" if mong is None else ("bỏ sót" if thuc is None else "sai số")
            print(f"  [{loai}] {cau}")
            print(f"        mong đợi {mong!r} · nhận được {thuc!r}")
    return {"ten": "Trích số điện thoại", "dat": dung, "tong": tong, "muc_tieu": 0.95}


# --- Câu 1c và câu 3 · cần dịch vụ ngoài --------------------------------------


def bao_phan_chua_do() -> list[dict]:
    # Bộ câu hỏi chatbot nằm ở thư mục khác vì nó do phần chatbot dùng, và có cả
    # chiều "phải trả lời" chứ không chỉ chiều từ chối. Một con bot từ chối mọi
    # thứ sẽ đạt 100% nếu chỉ đo chiều từ chối, nên hai chiều phải đi cùng nhau.
    import json as _json
    ngoai_p = THU_MUC.parent / "chatbot" / "bo_cau_hoi.json"
    ngoai = _json.loads(ngoai_p.read_text(encoding="utf-8"))
    cv = json.loads(
        (THU_MUC.parent / "cv" / "dap_an.json").read_text(encoding="utf-8")
    )
    tieu_de("PHẦN CHƯA ĐO ĐƯỢC Ở ĐÂY")
    print("Hai hạng mục dưới đây cần Qdrant và Gemini đang chạy, nên bộ này chỉ")
    print("chuẩn bị sẵn dữ liệu chứ không tự chấm. Chạy khi đã dựng đủ dịch vụ.\n")
    tu_choi = sum(1 for c in ngoai["cau_hoi"] if c["loai"] == "phai_tu_choi")
    tra_loi = len(ngoai["cau_hoi"]) - tu_choi
    print(f"  Bộ câu hỏi chatbot       : {tu_choi} câu phải từ chối, {tra_loi} câu phải trả lời")
    print("     chạy bằng: python -m scripts.nghiem_thu_chatbot")
    print(f"  Độ chính xác đọc CV      : {len(cv)} hồ sơ mẫu kèm đáp án")
    print(f"     mục tiêu: ≥ 80% trường đúng, 0% suy diễn")
    print("\n  Spec đặt mốc 30 CV mẫu; hiện có 6. Cần bổ sung trước khi lấy số")
    print("  này làm bằng chứng trong báo cáo.")
    return []


def main() -> int:
    print("ĐO CHẤT LƯỢNG HỆ THỐNG — theo docs/design/07 §7")

    bang = [do_y_dinh(), do_so_dien_thoai()]
    bao_phan_chua_do()

    tieu_de("TỔNG HỢP")
    print(f"{'Hạng mục':<26}{'Kết quả':>12}{'Tỷ lệ':>10}{'Mục tiêu':>11}  Đạt")
    tat_ca_dat = True
    for d in bang:
        ty_le = d["dat"] / d["tong"]
        ok = ty_le >= d["muc_tieu"]
        tat_ca_dat = tat_ca_dat and ok
        print(f"{d['ten']:<26}{d['dat']:>6}/{d['tong']:<5}{ty_le:>9.1%}{d['muc_tieu']:>10.0%}"
              f"  {'có' if ok else 'KHÔNG'}")
    print()
    print("Tất cả hạng mục đo được đều đạt." if tat_ca_dat
          else "Có hạng mục chưa đạt mục tiêu — xem chi tiết ở trên.")

    # Mã thoát phải nói cùng một điều với màn hình.
    #
    # Bản cũ luôn thoát 0, kể cả khi bảng in ra "KHÔNG". Ai chạy script này
    # trong một chuỗi lệnh — hay đọc kết quả của CI — sẽ thấy "thành công"
    # trong khi có hạng mục chưa đạt mục tiêu. Một phép đo nói dối về chính
    # nó thì tệ hơn là không đo.
    return 0 if tat_ca_dat else 1


if __name__ == "__main__":
    sys.exit(main())
