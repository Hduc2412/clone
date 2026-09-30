"""Hàng đợi hỗ trợ — việc cần người, tách khỏi hàng đợi tuyển dụng.

## Vì sao là hàng đợi thứ hai chứ không gộp vào hàng đợi đang có

`/admin/queue` giữ những hồ sơ **đã đủ điều kiện sơ bộ và đã chọn đơn** — việc ở
đó là gọi điện xác nhận rồi chốt. Hàng đợi này giữ thứ khác hẳn: người chưa đủ
điều kiện muốn hỏi thêm, người muốn tư vấn chuyện học, người muốn gặp mặt.

Trộn hai loại vào một chỗ thì việc gấp lẫn với việc dài hạn. Một nhân viên mở
hàng đợi ra thấy hai mươi dòng, không phân biệt được dòng nào là hồ sơ sắp chốt
và dòng nào là câu hỏi có thể trả lời cuối ngày — nên họ sẽ xử theo thứ tự thời
gian, và hồ sơ sắp chốt nằm đợi sau một câu hỏi về học phí.

Quan trọng hơn: gộp chung sẽ buộc phải nới **chốt chặn đăng ký**. Chốt hiện tại
từ chối tạo hồ sơ đăng ký khi đơn chưa đạt điều kiện, và đó là thứ giữ cho hàng
đợi tuyển dụng chỉ chứa hồ sơ dùng được. Cho người chưa đủ điều kiện đi qua cửa
ấy là phá đúng cái chốt vừa siết.

## Không lưu dữ liệu sức khỏe

Loại `hoc_tap` và những yêu cầu phát sinh từ chuyện sức khỏe đều **không ghi bệnh
gì**. Hệ thống chỉ biết "người này muốn được tư vấn", không biết vì sao. Chẩn
đoán bệnh theo người ta đi rất xa nếu lộ, mà giá trị nghiệp vụ của việc lưu nó
bằng không — buổi khám mới là chỗ kết luận.

## Ảnh chụp kết quả đối chiếu đi kèm

Mỗi yêu cầu mang theo `advice_block`: đúng khối chữ ứng viên đã nhìn thấy lúc
bấm nút. Nhân viên gọi lại đọc được **chính thứ khách đã đọc**, thay vì phải tự
dựng lại rồi đoán xem khách đang hiểu thế nào. Đây là bản chụp cố định, không
đổi kể cả khi hồ sơ hay đơn thay đổi về sau.
"""
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, ReturnDocument

from pymongo.errors import DuplicateKeyError

from app.db.common import get_db, now, strip_id


COLLECTION = "support_requests"

# Ba loại việc. Tách ra vì chúng cần người khác nhau và gấp khác nhau: tư vấn
# học là việc của người phụ trách đào tạo, xin gặp là việc của người xếp lịch.
KIND_NHAN_TIN = "nhan_tin"
KIND_HOC_TAP = "hoc_tap"
KIND_GAP_MAT = "gap_mat"
KINDS = (KIND_NHAN_TIN, KIND_HOC_TAP, KIND_GAP_MAT)

STATUS_CHO = "cho_xu_ly"
STATUS_DANG_XU_LY = "dang_xu_ly"
STATUS_XONG = "da_xong"
STATUS_HUY = "da_huy"
STATUSES = (STATUS_CHO, STATUS_DANG_XU_LY, STATUS_XONG, STATUS_HUY)

PROJECTION = {"_id": 0}


async def ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    await db[COLLECTION].create_index([("code", ASCENDING)], unique=True)
    # Hàng đợi đọc theo trạng thái, ai chờ lâu nhất lên đầu.
    await db[COLLECTION].create_index([("status", ASCENDING), ("created_at", ASCENDING)])
    await db[COLLECTION].create_index([("assigned_to", ASCENDING), ("created_at", DESCENDING)])
    await db[COLLECTION].create_index([("session_id", ASCENDING), ("created_at", DESCENDING)])

    # Chống trùng bằng INDEX, không bằng đọc-rồi-ghi.
    #
    # Bản trước tra `tim_yeu_cau_dang_cho` rồi mới `insert_one`. Hai lần bấm gần
    # nhau thì cả hai truy vấn đều thấy "chưa có", cả hai đều ghi, và hàng đợi có
    # hai việc cho cùng một người. Khoảng hở ấy đo được: bản rà soát 30/09 tái
    # hiện bằng cách cho hai lần kiểm tra chạy đồng thời, ra hai bản ghi 201.
    #
    # Dùng `dang_mo` thay vì lọc theo `status` vì `partialFilterExpression` của
    # MongoDB **không nhận `$in`** — chỉ `$eq`, `$exists` và vài toán tử so sánh.
    # Nên trạng thái mở được đánh dấu bằng đúng một cờ, và cờ ấy được **xóa** khi
    # yêu cầu đóng lại. Xóa chứ không đặt `False`: giá trị `False` vẫn nằm trong
    # index, và khách quay lại hỏi tiếp sẽ bị chặn oan.
    await db[COLLECTION].create_index(
        [
            ("session_id", ASCENDING),
            ("kind", ASCENDING),
            ("job_order_code", ASCENDING),
        ],
        unique=True,
        partialFilterExpression={"dang_mo": {"$eq": True}},
        name="mot_yeu_cau_dang_mo_moi_loai_moi_don",
    )


async def create_request(document: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Tạo yêu cầu. Trả `(bản ghi, có phải bản mới)`.

    `False` nghĩa là phiên này đã có một yêu cầu **đang mở** cùng loại cùng đơn, và
    hàm trả lại chính nó. Đây là đường chống trùng thật: index duy nhất chặn ở tầng
    dữ liệu, nên hai lần bấm cùng lúc chỉ ra một bản ghi — khác với đọc-rồi-ghi,
    nơi cả hai lần kiểm tra đều thấy "chưa có".

    Trả thêm cờ chứ không chỉ trả bản ghi, vì nơi gọi cần biết để không ghi thông
    báo lần thứ hai cho cùng một việc.
    """
    full = {
        **document,
        "status": STATUS_CHO,
        # Cờ đánh dấu yêu cầu đang mở — xem index ở `ensure_indexes`.
        "dang_mo": True,
        "assigned_to": None,
        "handled_at": None,
        "reply": None,
        # Thông báo cho nhân viên đã ghi được chưa. `None` là chưa.
        #
        # Tách khỏi việc tạo yêu cầu vì hai việc này hỏng độc lập: bản rà soát
        # 30/09 dựng cảnh `create_notification` ném ngoại lệ, và kết quả là yêu cầu
        # đã lưu nhưng khách nhận 500 — rồi gửi lại thì nhánh chống trùng trả 201
        # mà **vẫn không có thông báo nào**, nên nhân viên không bao giờ biết.
        "notified_at": None,
        "created_at": now(),
        "updated_at": now(),
    }
    try:
        await get_db()[COLLECTION].insert_one(dict(full))
    except DuplicateKeyError:
        dang_mo = await tim_yeu_cau_dang_cho(
            session_id=document["session_id"],
            kind=document["kind"],
            job_order_code=document.get("job_order_code"),
        )
        # Bản ghi vừa bị đóng giữa lúc chèn và lúc tra lại thì không còn "đang mở".
        # Rất hiếm, nhưng trả `None` ra ngoài sẽ thành `AttributeError` ở nơi gọi.
        if dang_mo is None:
            raise
        return dang_mo, False
    return strip_id(full), True


async def danh_dau_da_thong_bao(code: str) -> None:
    """Ghi lại rằng thông báo cho nhân viên đã tới nơi.

    Không có mốc này thì không phân biệt được "đã báo" với "báo hỏng" — và lần gửi
    lại sẽ im lặng bỏ qua, để yêu cầu nằm trong bảng mà không ai biết.
    """
    await get_db()[COLLECTION].update_one(
        {"code": code}, {"$set": {"notified_at": now(), "updated_at": now()}}
    )


async def tim_yeu_cau_dang_cho(
    *, session_id: str, kind: str, job_order_code: str | None
) -> dict[str, Any] | None:
    """Yêu cầu cùng loại, cùng đơn, của cùng phiên, **chưa ai xử lý xong**.

    Dùng để bấm hai lần không tạo hai việc. Nút gửi nằm cuối một màn hình dài,
    mạng di động thì chậm, và không có gì nhúc nhích trong một giây — người ta bấm
    lại. Mỗi lần bấm một dòng thì hai nhân viên nhận hai yêu cầu của cùng một
    người rồi gọi cho họ hai lần.

    Chỉ tính yêu cầu **đang mở**. Đã xử lý xong mà khách quay lại hỏi tiếp thì đó
    là một việc mới thật, không phải bấm nhầm — chặn nó là bịt đường của người cần
    hỏi thêm.

    Cũng chỉ gộp khi **cùng loại và cùng đơn**: xin gặp mặt về DH-0001 và hỏi
    chuyện học là hai việc khác nhau, dù cùng một người gửi trong một phút.
    """
    return await get_db()[COLLECTION].find_one(
        {
            "session_id": session_id,
            "kind": kind,
            "job_order_code": job_order_code,
            "status": {"$in": [STATUS_CHO, STATUS_DANG_XU_LY]},
        },
        PROJECTION,
        sort=[("created_at", DESCENDING)],
    )


async def get_request(code: str) -> dict[str, Any] | None:
    return await get_db()[COLLECTION].find_one({"code": code}, PROJECTION)


async def list_requests(
    *,
    status: str | None = STATUS_CHO,
    kind: str | None = None,
    assigned_to: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    query: dict[str, Any] = {}
    if status is not None:
        query["status"] = status
    if kind is not None:
        query["kind"] = kind
    if assigned_to is not None:
        query["assigned_to"] = assigned_to
    cursor = (
        get_db()[COLLECTION]
        .find(query, PROJECTION)
        # Tăng dần: ai chờ lâu nhất lên đầu. Cùng lý do như hàng đợi tuyển dụng.
        .sort([("created_at", ASCENDING)])
        .limit(limit)
    )
    return [document async for document in cursor]


async def list_for_session(session_id: str, limit: int = 20) -> list[dict[str, Any]]:
    """Yêu cầu của chính phiên này — để khách xem lại mình đã hỏi gì."""
    cursor = (
        get_db()[COLLECTION]
        .find({"session_id": session_id}, PROJECTION)
        .sort([("created_at", DESCENDING)])
        .limit(limit)
    )
    return [document async for document in cursor]


async def claim(code: str, *, email: str) -> dict[str, Any] | None:
    """Nhận xử lý. Trả `None` nếu người khác vừa nhận trước.

    Điều kiện `assigned_to: None` nằm ngay trong câu cập nhật, không phải đọc
    rồi ghi hai bước — hai người bấm cùng lúc thì một người nhận được, người kia
    biết ngay là trượt. Cùng cách với `/admin/queue`.
    """
    return await get_db()[COLLECTION].find_one_and_update(
        {"code": code, "assigned_to": None, "status": STATUS_CHO},
        {
            "$set": {
                "assigned_to": email,
                "status": STATUS_DANG_XU_LY,
                "updated_at": now(),
            }
        },
        projection=PROJECTION,
        return_document=ReturnDocument.AFTER,
    )


async def close_request(
    code: str, *, email: str, reply: str, status: str = STATUS_XONG
) -> dict[str, Any] | None:
    return await get_db()[COLLECTION].find_one_and_update(
        {"code": code},
        {
            "$set": {
                "status": status,
                "reply": reply,
                "handled_by": email,
                "handled_at": now(),
                "updated_at": now(),
            },
            # Xóa cờ, không đặt `False`: giá trị `False` vẫn nằm trong index duy
            # nhất, và khách quay lại hỏi tiếp sẽ bị chặn oan.
            "$unset": {"dang_mo": ""},
        },
        projection=PROJECTION,
        return_document=ReturnDocument.AFTER,
    )


async def count_waiting(kind: str | None = None) -> int:
    query: dict[str, Any] = {"status": STATUS_CHO}
    if kind is not None:
        query["kind"] = kind
    return await get_db()[COLLECTION].count_documents(query)
