"""Bộ nhớ dùng chung của một phiên — nơi hai hệ trả lời nhìn thấy nhau.

Đọc `app/memory/__init__.py` trước: ở đó có luật cứng của gói này, rằng **câu trả
lời không bao giờ đi qua đây**, chỉ có câu hỏi nguyên văn của ứng viên và nhãn
chủ đề do luật từ khóa gán.

## Một bản ghi cho một phiên

Không lưu từng lượt: `messages` (khung chat) và `advisor_turns` (engine tư vấn) đã
lưu đầy đủ lượt của mỗi bên rồi. Gói này chỉ giữ phần **hai bên cùng cần**, gom
lại thành một bản ghi nhỏ đọc được trong một lần truy vấn.

Lý do không gộp hai bảng kia lại mà đọc: chúng thuộc về hai bên khác nhau, hình
dạng khác nhau, và việc đọc chéo sẽ buộc mỗi bên phải hiểu lược đồ của bên kia —
đúng cái ràng buộc mà `tests/test_advisor_boundary.py` dựng lên để tránh.

## Vì sao đếm số lần hỏi

`so_lan` không phải để thống kê cho đẹp. Một người hỏi ba lần về chi phí thì mối
lo của họ là tiền, và điều đó đáng để **nhân viên biết trước khi bấm số gọi**,
cũng như để con tư vấn hiểu rằng câu trả lời lần trước chưa làm khách yên tâm.
Lặp lại đúng câu cũ lần thứ tư là cách chắc chắn nhất để mất một ứng viên.

## Giới hạn để một phiên không phình

Chủ đề thì hữu hạn (mười nhãn trong `app/memory/topics.py`), nên `moi_quan_tam`
tự nó đã có trần. Phần cần chặn là câu hỏi nguyên văn: chỉ giữ **câu gần nhất**
của mỗi chủ đề, cắt ở `DAI_TOI_DA` ký tự. Giữ cả lịch sử ở đây là chép lại
`messages` lần thứ hai, mà bản chép ấy thì không ai bảo trì.
"""
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING

from app.db.common import get_db, now


COLLECTION = "session_memory"

# Hai bên được phép ghi. Ghi thẳng chuỗi tự do vào đây thì sáu tháng sau không ai
# biết `"bot"` với `"assistant"` có phải một hay không.
BEN_CHAT = "chat"
BEN_TU_VAN = "tu_van"
CAC_BEN = (BEN_CHAT, BEN_TU_VAN)

# Câu hỏi dài hơn thì cắt. Bộ nhớ này đi vào prompt của cả hai bên, nên mỗi ký tự
# ở đây là ký tự lấy mất của phần dữ liệu thật.
DAI_TOI_DA = 160

PROJECTION = {"_id": 0}


async def ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    await db[COLLECTION].create_index([("session_id", ASCENDING)], unique=True)


async def lay(session_id: str) -> dict[str, Any] | None:
    return await get_db()[COLLECTION].find_one({"session_id": session_id}, PROJECTION)


async def dat_don_dang_xet(session_id: str, job_order_code: str) -> None:
    """Ghi lại đơn ứng viên đang xem.

    Đây là mẩu thông tin có giá trị nhất chảy từ engine tư vấn sang khung chat.
    Trước đó khung chat phải **đoán đơn nào bằng cách dò tên tỉnh trong câu hỏi**
    (`app/rag/job_lookup.py`) — nên khách đang mở đơn Tokyo mà hỏi trống không
    "đơn này lương bao nhiêu" thì nó chịu, hoặc tệ hơn là vớ nhầm một đơn Tokyo
    khác rồi trả lời rất trôi chảy bằng số của đơn không liên quan.
    """
    await get_db()[COLLECTION].update_one(
        {"session_id": session_id},
        {
            "$set": {"job_order_code": job_order_code, "job_order_set_at": now()},
            "$setOnInsert": {"session_id": session_id, "created_at": now()},
        },
        upsert=True,
    )


async def ghi_moc_tu_van(session_id: str, *, giai_doan: str, nhan: str) -> None:
    """Ghi **mốc** của phòng tư vấn hồ sơ — một dòng trạng thái, không có nội dung.

    ## Vì sao chỉ ghi mốc

    Đây là mức thứ hai của "hai mức bộ nhớ". Bản tóm tắt đầy đủ về cuộc trò
    chuyện đi kèm yêu cầu hỗ trợ, cho **nhân viên** đọc. Chỗ này chỉ nhận một
    dòng kiểu *"đã tư vấn tới bước đối chiếu"*.

    Lý do nằm ở bên đọc nó: **khung chat**. Khung chat làm hỏi đáp chung theo tài
    liệu công ty, và kho tài liệu ấy còn rác nhận dạng ảnh ở 24/32 đoạn. Đưa nội
    dung tư vấn vào đây là mời nó trả lời sâu về hồ sơ, matching và lộ trình học
    bằng đúng cái kho đó — chỗ dễ nói sai con số nhất.

    Nên bất biến của gói `app/memory` vẫn nguyên: **chở câu hỏi, không chở câu
    trả lời**. Một mốc trạng thái không phải là câu trả lời; nó chỉ giúp khung
    chat biết khách không phải người mới, và biết đường chỉ sang phòng tư vấn.
    """
    await get_db()[COLLECTION].update_one(
        {"session_id": session_id},
        {
            "$set": {
                "moc_tu_van": {"giai_doan": giai_doan, "nhan": nhan, "luc": now()}
            },
            "$setOnInsert": {"session_id": session_id, "created_at": now()},
        },
        upsert=True,
    )


async def ghi_moi_quan_tam(
    session_id: str, *, chu_de: str, cau_hoi: str, ben: str
) -> None:
    """Ghi một lượt ứng viên hỏi về `chu_de`.

    `cau_hoi` lưu **nguyên văn lời ứng viên**, không phải câu trả lời của bot.
    Đây là chỗ luật cứng của gói này được thi hành bằng mã chứ không bằng lời
    dặn: hàm không có tham số nào nhận câu trả lời, nên không ai lỡ tay truyền
    vào được.
    """
    if ben not in CAC_BEN:
        raise ValueError(f"ben phải là một trong {CAC_BEN}, nhận được {ben!r}")

    goc = " ".join(cau_hoi.split())[:DAI_TOI_DA]
    luc = now()

    ket_qua = await get_db()[COLLECTION].update_one(
        {"session_id": session_id, "moi_quan_tam.chu_de": chu_de},
        {
            "$inc": {"moi_quan_tam.$.so_lan": 1},
            "$set": {
                "moi_quan_tam.$.lan_cuoi": luc,
                "moi_quan_tam.$.cau_gan_nhat": goc,
                "moi_quan_tam.$.ben_gan_nhat": ben,
                "updated_at": luc,
            },
        },
    )
    if ket_qua.matched_count:
        return

    await get_db()[COLLECTION].update_one(
        {"session_id": session_id},
        {
            "$push": {
                "moi_quan_tam": {
                    "chu_de": chu_de,
                    "so_lan": 1,
                    "lan_dau": luc,
                    "lan_cuoi": luc,
                    "cau_gan_nhat": goc,
                    "ben_gan_nhat": ben,
                }
            },
            "$set": {"updated_at": luc},
            "$setOnInsert": {"session_id": session_id, "created_at": luc},
        },
        upsert=True,
    )


async def ghi_da_giai_thich(session_id: str, *, chu_de: str, ben: str) -> None:
    """Đánh dấu một chủ đề đã được bên nào đó giải thích.

    Chỉ ghi **nhãn chủ đề**, không ghi lời đã nói. Bên kia đọc được "chi phí đã
    được engine tư vấn giải thích", và nó phải tự dựng lại câu trả lời từ nguồn
    của chính nó. Xem `app/memory/__init__.py`.
    """
    if ben not in CAC_BEN:
        raise ValueError(f"ben phải là một trong {CAC_BEN}, nhận được {ben!r}")

    luc = now()
    ket_qua = await get_db()[COLLECTION].update_one(
        {"session_id": session_id, "da_giai_thich.chu_de": chu_de},
        {"$set": {"da_giai_thich.$.luc": luc, "da_giai_thich.$.ben": ben,
                  "updated_at": luc}},
    )
    if ket_qua.matched_count:
        return

    await get_db()[COLLECTION].update_one(
        {"session_id": session_id},
        {
            "$push": {"da_giai_thich": {"chu_de": chu_de, "ben": ben, "luc": luc}},
            "$set": {"updated_at": luc},
            "$setOnInsert": {"session_id": session_id, "created_at": luc},
        },
        upsert=True,
    )


async def xoa(session_id: str) -> None:
    """Xóa bộ nhớ của một phiên. Dùng khi ứng viên bấm bắt đầu lại."""
    await get_db()[COLLECTION].delete_one({"session_id": session_id})


async def thong_ke(since: Any = None) -> dict[str, Any]:
    """Những chủ đề ứng viên hỏi nhiều nhất, trên toàn bộ dữ liệu thật.

    Đây là số liệu nghiệp vụ chứ không phải số liệu kỹ thuật: nó nói cho công ty
    biết người đang tìm hiểu lo về cái gì nhất. Nếu chi phí đứng đầu bảng thì
    trang giới thiệu đang nói chưa đủ rõ về chi phí, và đó là việc sửa được.
    """
    query: dict[str, Any] = {}
    if since is not None:
        query["updated_at"] = {"$gte": since}

    duong_ong = [
        {"$match": query},
        {"$unwind": "$moi_quan_tam"},
        {
            "$group": {
                "_id": "$moi_quan_tam.chu_de",
                "so_luot_hoi": {"$sum": "$moi_quan_tam.so_lan"},
                "so_phien": {"$sum": 1},
            }
        },
        {"$sort": {"so_luot_hoi": -1}},
    ]
    theo_chu_de = [
        {
            "chu_de": row["_id"],
            "so_luot_hoi": row["so_luot_hoi"],
            "so_phien": row["so_phien"],
        }
        async for row in get_db()[COLLECTION].aggregate(duong_ong)
    ]
    return {
        "theo_chu_de": theo_chu_de,
        "so_phien_co_bo_nho": await get_db()[COLLECTION].count_documents(query),
    }
