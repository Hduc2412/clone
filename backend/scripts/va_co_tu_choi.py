"""Vá cờ `is_fallback` cho những câu mô hình tự từ chối đã lưu từ trước.

Cờ chỉ được gắn từ lúc sửa `chat_service` trở đi. Những câu đã lưu trước đó vẫn
nằm trong database mà không mang cờ, nên `get_fallback_rate` đếm chúng như câu
trả lời thành công — và con số đưa vào báo cáo vì thế cao hơn thực tế.

Chạy thử (không ghi gì):
    venv\\Scripts\\python.exe -m scripts.va_co_tu_choi

Ghi thật:
    venv\\Scripts\\python.exe -m scripts.va_co_tu_choi --write

## Vì sao phải chạy thử trước

Đây là lệnh sửa dữ liệu đã lưu, và nó sửa đúng con số sẽ đưa vào báo cáo. Một
mẫu nhận diện quá rộng sẽ gắn cờ cho câu trả lời thật, làm tỷ lệ hỏng nhìn cao
hơn thực tế — sai theo chiều ngược lại, và khó phát hiện hơn nhiều. Vì vậy mặc
định là in ra để người đọc, chỉ ghi khi được yêu cầu rõ ràng.
"""
import asyncio
import sys

import app  # noqa: F401  — đặt stdout về UTF-8 để in được tiếng Việt
from app.conversation.fallback_messages import ALL_FALLBACKS, looks_like_refusal
from app.db.database import close_db, get_db, init_db


async def main() -> int:
    ghi = "--write" in sys.argv
    await init_db()
    try:
        db = get_db()
        can_va: list[dict] = []
        async for row in db.messages.find(
            {"role": "assistant", "is_fallback": {"$ne": True}},
            {"_id": 1, "content": 1},
        ):
            content = row.get("content", "")
            # Bốn câu dựng sẵn đã được `get_fallback_rate` đối chiếu theo nội
            # dung, nên không cần vá. Chỉ vá câu do mô hình tự viết.
            if content in ALL_FALLBACKS:
                continue
            if looks_like_refusal(content):
                can_va.append(row)

        print(f"Tìm thấy {len(can_va)} câu mô hình tự từ chối mà chưa có cờ.\n")
        for row in can_va[:10]:
            print("  -", row.get("content", "")[:110].replace("\n", " "))
        if len(can_va) > 10:
            print(f"  … và {len(can_va) - 10} câu nữa.")

        if not can_va:
            return 0
        if not ghi:
            print("\nĐây là lượt chạy thử, chưa ghi gì. Thêm --write để ghi thật.")
            return 0

        result = await db.messages.update_many(
            {"_id": {"$in": [row["_id"] for row in can_va]}},
            {"$set": {"is_fallback": True}},
        )
        print(f"\nĐã gắn cờ cho {result.modified_count} bản ghi.")
        return 0
    finally:
        await close_db()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
