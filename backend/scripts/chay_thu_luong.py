"""Chạy thử toàn luồng tư vấn qua HTTP thật, in ra cho người đọc theo dõi.

## Vì sao cần một script chứ không gõ tay

Bản chạy tay ngày 22/09/2026 in ra "0 đơn" ở bước đối chiếu, và mất một lúc mới
biết đó là do script gõ nhầm khóa (`items` thay vì `matches`) chứ không phải hệ
thống hỏng. Một lần đọc nhầm như vậy trong buổi bảo vệ là đủ để mất thời gian
giải thích thứ không có thật.

Script này đọc đúng khóa mà API trả về, và **dừng ngay khi gặp bước hỏng** thay
vì chạy tiếp rồi in ra một bảng trông như bình thường.

## Cần gì để chạy

MongoDB, Qdrant và backend phải đang chạy. Mỗi lượt chat tốn một lượt gọi mô
hình — hạn mức gói miễn phí là 20 lượt/ngày/model, nên script chỉ hỏi 2 câu.

    python scripts/chay_thu_luong.py http://127.0.0.1:8020
"""
import io
import sys

import requests

# Không có dòng này thì console Windows (cp1252) nuốt mọi chữ có dấu.
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

GOC = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8020"

HO_SO_MAU = {
    "mode": "manual",
    "fields": {
        "full_name": "Nguyễn Thị Lan",
        "birth_year": 1999,
        "gender": "Nữ",
        "education_level": "Cao đẳng",
        "japanese_level": "N4",
        "experience_years": 3,
        "care_experience": True,
        "phone": "0912345678",
    },
    "preferences": {"desired_prefecture": "Tokyo"},
}


def tieu_de(chu: str) -> None:
    print(f"\n{'=' * 72}\n  {chu}\n{'=' * 72}")


def dung(ly_do: str) -> None:
    print(f"\nDỪNG: {ly_do}")
    sys.exit(1)


def main() -> None:
    khach_a, khach_b = requests.Session(), requests.Session()

    tieu_de("1 · HAI KHÁCH MỞ PHIÊN")
    try:
        a = khach_a.post(f"{GOC}/public/phien", timeout=20).json()["session_id"]
        khach_b.post(f"{GOC}/public/phien", timeout=20)
    except requests.RequestException as loi:
        dung(f"không gọi được backend ở {GOC} ({loi})")
    print(f"  Khách A: {a}")
    print(f"  Cookie đã nhận: {'xkld_journey' in khach_a.cookies}")

    tieu_de("2 · KHÁCH A KHAI HỒ SƠ")
    r = khach_a.post(f"{GOC}/public/profiles", json=HO_SO_MAU, timeout=30)
    if not r.ok:
        dung(f"tạo hồ sơ hỏng: HTTP {r.status_code} · {r.text[:200]}")
    ho_so = r.json()
    print(f"  {ho_so['code']} · trạng thái {ho_so['status']} · "
          f"nguồn họ tên {ho_so['fields']['full_name']['source']}")

    tieu_de("3 · KHÁCH B THỬ ĐỌC HỒ SƠ CỦA KHÁCH A")
    khong_cookie = requests.get(f"{GOC}/public/profiles/{a}", timeout=20)
    cookie_cua_b = khach_b.get(f"{GOC}/public/profiles/{a}", timeout=20)
    cua_chinh_minh = khach_a.get(f"{GOC}/public/profiles/{a}", timeout=20)

    print(f"  Không cookie, chỉ có mã trên URL : HTTP {khong_cookie.status_code}")
    print(f"  Cookie của B, đổi mã trên URL    : HTTP {cookie_cua_b.status_code}")
    print(f"  Khách A dùng cookie của chính A  : HTTP {cua_chinh_minh.status_code}")
    if (khong_cookie.status_code, cookie_cua_b.status_code) != (401, 403):
        dung("hàng rào quyền truy cập KHÔNG giữ — phải là 401 rồi 403")
    print("  → hàng rào giữ đúng")

    tieu_de("4 · ĐỐI CHIẾU ĐƠN")
    r = khach_a.get(f"{GOC}/public/matches/{a}", timeout=60)
    if not r.ok:
        dung(f"đối chiếu hỏng: HTTP {r.status_code} · {r.text[:200]}")
    kq = r.json()
    # Khóa là `matches`, không phải `items`. Đây đúng là chỗ bản chạy tay gõ nhầm.
    cac_don = kq["matches"]
    print(f"  Xét {kq['total_considered']} đơn · đạt điều kiện {kq['eligible_count']}")
    for don in cac_don[:3]:
        print(f"    #{don['rank']} {don['code']} · {don['title']} · "
              f"{don['prefecture']} · {don['score']}/100")
    if kq["missing_info"]:
        print("  Hệ thống còn cần biết:")
        for cau in kq["missing_info"]:
            print(f"    - {cau}")

    tieu_de("5 · CHAT — CÓ BIẾT MÌNH ĐANG NÓI VỚI AI KHÔNG")
    for cau in [
        "Với hồ sơ của em thì em đi được không ạ?",
        "Thế em cần chuẩn bị thêm gì nữa?",
    ]:
        r = khach_a.post(f"{GOC}/chat", json={"message": cau}, timeout=120)
        if not r.ok:
            dung(f"chat hỏng: HTTP {r.status_code} · {r.text[:200]}")
        d = r.json()
        print(f"\n  HỎI: {cau}")
        print(f"  (ý định {d['intent']} · dự phòng {d['is_fallback']} · "
              f"{len(d['sources'])} nguồn)")
        print("  ĐÁP: " + d["answer"].replace("\n", "\n       "))

    tieu_de("XONG")
    print("  Mọi bước đều qua. Kiểm tra thêm bằng mắt:")
    print("   - câu trả lời có nhắc đúng thông tin khách đã khai không")
    print("   - lượt thứ hai có mở đầu bằng lời chào không (không được)")
    print("   - có kết thúc bằng số tổng đài không (chỉ khi thật sự cần)")


if __name__ == "__main__":
    main()
