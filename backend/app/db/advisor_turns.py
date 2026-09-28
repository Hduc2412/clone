"""Lượt hỏi đáp trong phòng tư vấn.

Lưu lại vì ba lý do, và lý do thứ ba là quan trọng nhất:

1. **Khách tải lại trang không mất cuộc trò chuyện.** Hành trình này kéo dài
   nhiều ngày — hỏi hôm nay, bàn với gia đình, hôm sau quay lại hỏi tiếp.

2. **Bot nhớ được vài lượt gần nhất** để hiểu câu "còn cái kia thì sao".

3. **Nhân viên đọc được ứng viên đã hỏi gì trước khi gọi điện.** Đây mới là chỗ
   có giá trị thật: một người hỏi ba lần về chi phí thì mối lo của họ là tiền,
   và nhân viên biết điều đó trước khi bấm số sẽ nói chuyện khác hẳn.

## Lưu cả câu bị loại

Khi chốt hậu kiểm loại một câu trả lời của mô hình, bản ghi vẫn giữ `source` là
`khong_biet`. Đếm số lượt như vậy trên dữ liệu thật là **số liệu để bảo vệ**: nó
trả lời câu "làm sao biết bot không bịa" bằng tỉ lệ đo được, chứ không bằng lời
hứa trong tài liệu.

## Ba ô, không phải hai

Lúc đầu cột `source` chỉ có hai giá trị, và mọi lần bot không trả lời đều rơi vào
`khong_biet`. Đó là một lỗi đo lường nghiêm trọng, phát hiện ngày 28/09 khi hạn
mức cạn giữa một lượt nghiệm thu: mười câu không hề tới được mô hình, nhưng đều
được ghi là "bot cân nhắc rồi chịu không đoán".

Hậu quả không phải là thiếu vài dòng nhật ký. Tỉ lệ `khong_biet` chính là con số
đem đi bảo vệ, nên gộp chung nghĩa là **hệ thống càng hỏng thì chỉ số trung thực
trông càng đẹp** — mất mạng cả ngày thì tỉ lệ lên 100%. Một thước đo mà hỏng
hóc làm nó đẹp lên thì không đo gì cả.

Nên có ô thứ ba: `khong_goi_duoc`. Nó **không nằm trong mẫu số** của tỉ lệ, vì
tỉ lệ ấy nói về phán đoán của bot, còn ô này nói về việc dịch vụ có sống hay
không. Hai câu hỏi khác nhau thì hai con số khác nhau.
"""
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING

from app.db.common import get_db, now, strip_id


COLLECTION = "advisor_turns"

SOURCE_MO_HINH = "mo_hinh"
SOURCE_KHONG_BIET = "khong_biet"
# Không gọi được mô hình: mất mạng, hết hạn mức, dịch vụ quá tải. Tách khỏi
# `khong_biet` — xem phần "Ba ô, không phải hai" trong docstring đầu file.
SOURCE_KHONG_GOI_DUOC = "khong_goi_duoc"

# Chặn một phiên làm phình collection. Hai mươi lượt là đã quá dài cho một cuộc
# tư vấn về một đơn; quá đó thì vấn đề là cần gặp người, không phải hỏi thêm bot.
MAX_MOI_PHIEN = 40

PROJECTION = {"_id": 0}


async def ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    await db[COLLECTION].create_index(
        [("session_id", ASCENDING), ("job_order_code", ASCENDING), ("created_at", ASCENDING)]
    )
    await db[COLLECTION].create_index([("created_at", DESCENDING)])


async def add_turn(
    *,
    session_id: str,
    job_order_code: str,
    question: str,
    answer: str,
    source: str,
) -> dict[str, Any]:
    document = {
        "session_id": session_id,
        "job_order_code": job_order_code,
        "question": question,
        "answer": answer,
        "source": source,
        "created_at": now(),
    }
    await get_db()[COLLECTION].insert_one(dict(document))
    return strip_id(document)


async def list_turns(
    session_id: str, job_order_code: str, limit: int = 50
) -> list[dict[str, Any]]:
    cursor = (
        get_db()[COLLECTION]
        .find({"session_id": session_id, "job_order_code": job_order_code}, PROJECTION)
        .sort([("created_at", ASCENDING)])
        .limit(limit)
    )
    return [document async for document in cursor]


async def count_turns(session_id: str, job_order_code: str) -> int:
    return await get_db()[COLLECTION].count_documents(
        {"session_id": session_id, "job_order_code": job_order_code}
    )


async def thong_ke(since: Any = None) -> dict[str, Any]:
    """Đếm lượt theo nguồn câu trả lời.

    Đây là **số liệu trả lời câu "làm sao biết bot không bịa"** bằng đo đạc thay
    vì bằng lời hứa trong tài liệu. Mỗi lượt `khong_biet` là một lần bot chịu
    dừng lại: hoặc chốt hậu kiểm loại câu của mô hình, hoặc chính mô hình nhận là
    không biết, hoặc không gọi được mô hình.

    Hai nguyên nhân đó không tách ra ở đây: với người đọc số liệu, cả hai đều
    dẫn tới cùng một kết quả nhìn thấy được — ứng viên nhận câu "chưa có thông
    tin" kèm đường đi tiếp, thay vì một câu bịa nghe rất trôi chảy.

    Nhưng lượt **không gọi được mô hình** thì tách hẳn, và không tính vào mẫu số.
    Xem phần "Ba ô, không phải hai" ở đầu file.
    """
    query: dict[str, Any] = {}
    if since is not None:
        query["created_at"] = {"$gte": since}

    duong_ong = [
        {"$match": query},
        {"$group": {"_id": "$source", "so_luot": {"$sum": 1}}},
    ]
    theo_nguon = {
        row["_id"]: row["so_luot"]
        async for row in get_db()[COLLECTION].aggregate(duong_ong)
    }
    mo_hinh = theo_nguon.get(SOURCE_MO_HINH, 0)
    khong_biet = theo_nguon.get(SOURCE_KHONG_BIET, 0)
    khong_goi_duoc = theo_nguon.get(SOURCE_KHONG_GOI_DUOC, 0)
    # Mẫu số chỉ gồm những lượt mô hình thật sự được hỏi. Lượt không gọi được
    # nằm ngoài, vì nó nói về dịch vụ chứ không nói về phán đoán của bot.
    tong = mo_hinh + khong_biet

    return {
        "tong_luot": tong,
        "mo_hinh_tra_loi": mo_hinh,
        "bot_khong_doan": khong_biet,
        # Không nằm trong `tong_luot`. Con số này là chỉ số sức khỏe của dịch vụ:
        # nó lớn nghĩa là hết hạn mức hoặc mạng hỏng, không phải bot thận trọng.
        "khong_goi_duoc": khong_goi_duoc,
        # Làm tròn tới một chữ số thập phân. Ghi thêm chữ số nữa là gợi ý một độ
        # chính xác mà cỡ mẫu này chưa có.
        "ty_le_khong_doan": round(khong_biet * 100 / tong, 1) if tong else None,
        "so_phien": len(await get_db()[COLLECTION].distinct("session_id", query)),
        "so_don_da_hoi": len(await get_db()[COLLECTION].distinct("job_order_code", query)),
    }
