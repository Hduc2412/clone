"""Nghiệm thu khối đối chiếu, chạy trên database thật.

Diễn lại đúng kịch bản trong `docs/design/14`: một ứng viên nhập hồ sơ tay qua
API công khai, xác nhận, rồi xem danh sách đơn phù hợp. Không gọi mô hình ngôn
ngữ lần nào — toàn bộ điểm số và lời giải thích do Python sinh ra.

Chạy:  venv\\Scripts\\python.exe -m scripts.nghiem_thu_doi_chieu
"""
import asyncio
import json

from fastapi import Request

import app  # noqa: F401  — đặt stdout về UTF-8 để in được tiếng Việt
from app.auth.journey_security import create_journey_token
from app.api import matching as matching_api
from app.api import profiles as profiles_api
from app.db import candidate_profiles as profile_store
from app.db import job_orders as order_store
from app.db.database import close_db, init_db
from app.matching import explain
from app.services import matching_service


# Phải khớp `^[A-Za-z0-9-]{32,64}$` của `ProfileCreateRequest` — mã cũ
# `nghiem-thu-doi-chieu-001` (24 ký tự) làm script chết ngay bước 2.
SESSION = "nghiem-thu-doi-chieu-0000000000000001"


def http_request() -> Request:
    return Request({"type": "http", "headers": [], "client": ("127.0.0.1", 12345)})


def buoc(so: int, ten: str) -> None:
    print(f"\n{'─' * 78}\nBƯỚC {so} · {ten}\n{'─' * 78}")


#: Mã thoát khi không có gì để đo — cùng quy ước với các bộ đo khác.
KHONG_DO_DUOC = 3


async def main() -> int:
    """Diễn lại kịch bản, và KIỂM từng bước. Trả mã thoát.

    Bản trước in ra các phép so ("Giống hệt: True/False") nhưng không kiểm phép
    nào, rồi luôn in "✓ NGHIỆM THU ĐẠT" và thoát 0 — cùng lỗi với
    `nghiem_thu_agent` mà chủ đồ án bắt ngày 06/10. Một bộ nghiệm thu chỉ in ra
    là một bản trình diễn, không phải một phép đo.
    """
    hong: list[str] = []
    await init_db()
    try:
        buoc(1, "Kho đơn đem đối chiếu")
        pool = await matching_service.load_pool()
        public = await order_store.list_job_orders(order_store.public_filter(), limit=500)
        print(f"Đơn đã công khai (kho đối chiếu): {len(pool)}")
        print(f"Đơn thật sự hiển thị trên website: {len(public)}")
        print("Chênh lệch là đơn hết hạn hoặc tạm dừng — giữ lại để nhật ký")
        print("chứng minh được bộ lọc điều kiện đã chạy chứ không phải im lặng bỏ qua.")
        if not pool:
            print("\nChưa có đơn nào. Chạy `python -m scripts.seed_job_orders` trước.")
            return KHONG_DO_DUOC

        buoc(2, "Ứng viên nhập hồ sơ qua API công khai")
        db = order_store.get_db()
        await db[profile_store.COLLECTION].delete_many({"session_id": SESSION})
        created = await profiles_api.create_profile(
            profiles_api.ProfileCreateRequest(
                session_id=SESSION,
                fields={
                    "full_name": "Nguyễn Văn An",
                    "birth_year": 2003,
                    "gender": "Nam",
                    "education_level": "Cao đẳng",
                    "major": "Điều dưỡng",
                    "japanese_level": "N4",
                    "experience_years": 1,
                    "care_experience": True,
                    "phone": "0912345678",
                },
                preferences={
                    "desired_prefecture": "Tokyo",
                    "desired_employer_type": "Viện dưỡng lão",
                    "salary_expectation_jpy": 190000,
                    "budget_vnd": 150_000_000,
                },
            ),
            http_request(),
            journey_cookie=create_journey_token(SESSION),
        )
        print(f"Mã hồ sơ: {created['code']}  ·  trạng thái: {created['labels']['status']}")
        print(f"Vùng suy ra từ tỉnh: {created['labels']['desired_region_group']}")
        print(f"Nguồn của mọi giá trị: {created['fields']['full_name']['source']}")
        print(f"Còn thiếu: {created['missing_required'] or 'không thiếu gì'}")

        buoc(3, "Đối chiếu")
        result = await matching_api.matches_for_session(
            SESSION, http_request(), limit=5, refresh=False
        )
        print(f"Đã xét {result['total_considered']} đơn · {result['eligible_count']} đơn đạt")
        if not result["matches"]:
            # Hồ sơ demo (docs/design/14: N4, cao đẳng điều dưỡng, muốn Tokyo) phải
            # nộp được đơn. Không có đơn nào thì các bước sau cũng không có gì để xem.
            hong.append("hồ sơ demo không có đơn nào đạt")
            print("\n✗ NGHIỆM THU HỎNG: " + "; ".join(hong))
            return 1
        print(f"Nhật ký: {result['log_code']}  ·  dùng lại kết quả cũ: {result['from_cache']}")
        print(f"\n{result['disclaimer']}")

        buoc(4, "Lý do đơn đứng đầu — sinh hoàn toàn bằng mã")
        print(result["matches"][0]["explanation_block"])
        print(f"\nCâu tóm tắt cho ứng viên:\n  {result['matches'][0]['explanation_text']}")

        buoc(5, "Đơn bị loại và lý do bị loại")
        log = await matching_service.recommendation_logs.get_log(result["log_code"])
        rejected = [item for item in log["items"] if not item["eligible"]]
        print(f"{len(rejected)} đơn bị loại. Ba đơn đầu:\n")
        for item in rejected[:3]:
            ly_do = [
                f"{row['label']}: {row['requirement_text']} ≠ {row['candidate_text']}"
                for row in item["hard_rows"]
                if row["result"] == "KHONG_DAT"
            ]
            print(f"  {item['code']} · {item['title']}")
            for dong in ly_do:
                print(f"      ✗ {dong}")
            print(f"      điểm: {item['score']} · hạng: {item['rank']}")
        if not rejected:
            hong.append("không đơn nào bị loại — nhật ký không chứng minh được bộ lọc cứng đã chạy")
        for item in rejected:
            if not any(r["result"] == "KHONG_DAT" for r in item["hard_rows"]):
                hong.append(f"{item['code']} bị loại mà không ghi lý do KHÔNG ĐẠT nào")
            if item["rank"] is not None:
                # Đơn bị loại không có hạng: "hạng 3 · KHÔNG ĐẠT" cạnh nhau là mời
                # người đọc đem so sánh hai thứ không so được.
                hong.append(f"{item['code']} bị loại mà vẫn mang hạng {item['rank']}")

        buoc(6, "Chạy lại phải ra kết quả giống hệt")
        again = await matching_api.matches_for_session(
            SESSION, http_request(), limit=5, refresh=False
        )
        khoa = lambda r: json.dumps(  # noqa: E731
            [(m["code"], m["score"], m["rank"]) for m in r["matches"]], ensure_ascii=False
        )
        print(f"Lần 1: {khoa(result)}")
        print(f"Lần 2: {khoa(again)}")
        print(f"Giống hệt: {khoa(result) == khoa(again)}  ·  dùng lại bộ nhớ đệm: {again['from_cache']}")

        forced = await matching_api.matches_for_session(
            SESSION, http_request(), limit=5, refresh=True
        )
        print(f"Chạy lại cưỡng bức (bỏ qua bộ nhớ đệm): {khoa(forced)}")
        print(f"Vẫn giống hệt: {khoa(result) == khoa(forced)}")
        if khoa(result) != khoa(again):
            hong.append("chạy lại cho kết quả khác — mất tính tất định")
        if khoa(result) != khoa(forced):
            hong.append("chạy lại bỏ qua bộ nhớ đệm cho kết quả khác — mất tính tất định")

        buoc(7, "Hồ sơ mới điền một nửa vẫn phải thấy đơn")
        await db[profile_store.COLLECTION].delete_many({"session_id": SESSION + "-b"})
        thieu = await profiles_api.create_profile(
            profiles_api.ProfileCreateRequest(
                session_id=SESSION + "-b", fields={"full_name": "Trần Thị Bình"}
            ),
            http_request(),
            journey_cookie=create_journey_token(SESSION + "-b"),
        )
        log_b, _ = await matching_service.run_matching(thieu, trigger="public")
        print(f"Hồ sơ chỉ có họ tên · {log_b['eligible_count']}/{log_b['total_considered']} đơn đạt")
        print("Câu hỏi hệ thống sẽ hỏi tiếp:")
        for cau in log_b["missing_info"]:
            print(f"  · {cau}")
        if not log_b["eligible_count"]:
            # Nguyên tắc gốc của bộ đối chiếu: chưa biết không phải là không đạt.
            hong.append("hồ sơ chỉ có họ tên không thấy đơn nào — 'chưa rõ' đang bị coi là 'không đạt'")
        if not log_b["missing_info"]:
            hong.append("hồ sơ thiếu gần hết mà không sinh câu hỏi nào")

        buoc(8, "Dọn dẹp")
        await db[profile_store.COLLECTION].delete_many(
            {"session_id": {"$in": [SESSION, SESSION + "-b"]}}
        )
        await db[matching_service.recommendation_logs.COLLECTION].delete_many(
            {"profile_code": {"$in": [created["code"], thieu["code"]]}}
        )
        print("Đã xóa hồ sơ và nhật ký của lần nghiệm thu này.")
        print()
        if hong:
            print("✗ NGHIỆM THU HỎNG:")
            for h in hong:
                print(f"  ! {h}")
            return 1
        print("✓ NGHIỆM THU ĐẠT")
        return 0
    finally:
        await close_db()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
