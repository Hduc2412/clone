"""Tiện ích dùng chung cho các module dữ liệu nghiệp vụ.

`database.py` đã dài hơn một nghìn dòng và đang giữ toàn bộ collection cũ. Các
nghiệp vụ mới (đơn tuyển dụng, hồ sơ CV, phiếu tóm tắt, điểm nhân viên) đặt ở
module riêng để file đó không phình thêm, nhưng vẫn dùng chung một kết nối.

Chỉ `get_db` được lấy từ `database.py`, vì kết nối phải là một. Những tiện ích
còn lại định nghĩa tại chỗ thay vì nhập từ đó: phần đó do nhóm khác phát triển
song song, nhập chéo vào thì mỗi lần họ dọn dẹp file là phần này gãy theo.
"""
from datetime import UTC, datetime
from typing import Any

from app.db.database import get_db  # noqa: F401  (tái xuất cho các module dữ liệu)


def now() -> datetime:
    """Mốc thời gian ghi vào database, luôn theo UTC."""
    return datetime.now(UTC)


def strip_id(document: dict[str, Any] | None) -> dict[str, Any] | None:
    """Bỏ `_id` của MongoDB vì nó không tuần tự hóa được sang JSON."""
    if document is None:
        return None
    return {key: value for key, value in document.items() if key != "_id"}


def keep_allowed_nulls(
    fields: dict[str, Any],
    nullable: frozenset[str],
) -> dict[str, Any]:
    """Giữ `None` cho trường được phép xóa, bỏ `None` cho những trường còn lại.

    Router gọi `model_dump(exclude_unset=True)`, nên một khóa mang giá trị `None`
    nghĩa là người dùng cố ý muốn xóa trường đó — khác hẳn với "không gửi trường
    này". Nhưng có những trường phải luôn có giá trị: trạng thái đơn, tên đơn,
    tỉnh. Ghi `None` vào đó là làm hỏng bản ghi, nên với chúng thì bỏ qua.
    """
    return {
        key: value
        for key, value in fields.items()
        if value is not None or key in nullable
    }


def flatten_update(fields: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    """Đưa dữ liệu lồng nhau về dạng đường dẫn chấm cho toán tử `$set`.

    Gán thẳng `{"requirements": {"age_min": 20}}` sẽ **thay cả** object
    `requirements`, xóa mất những điều kiện khác của đơn hàng. Chuyển thành
    `{"requirements.age_min": 20}` để chỉ sửa đúng trường được gửi lên.
    """
    flat: dict[str, Any] = {}
    for key, value in fields.items():
        path = f"{prefix}{key}"
        if isinstance(value, dict):
            flat.update(flatten_update(value, prefix=f"{path}."))
        else:
            flat[path] = value
    return flat
