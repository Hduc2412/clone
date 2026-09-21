"""Tra danh mục đơn tuyển dụng khi câu hỏi nhắc tới một địa điểm ở Nhật.

## Vì sao cần

Kho tri thức và danh mục đơn hàng là **hai nửa tách rời** của hệ thống: kho giữ
tài liệu chính sách (Qdrant), danh mục giữ từng đơn cụ thể (MongoDB). Chatbot chỉ
đọc nửa thứ nhất, nên có những câu hệ thống biết câu trả lời mà chatbot vẫn chịu.

Ca thật: *"Học đơn ở Kaigo nhưng tôi muốn đi Tokyo thì có đi được không?"* — tra
kho thì lấy về sáu đoạn chẳng liên quan, trong đó có cả bài viết thư pháp; điểm
đoạn đầu 0,7116, đủ cao để không bị bộ lọc chặn. Trong khi danh mục có sẵn hai
đơn ở Tokyo đang tuyển.

## Nguyên tắc: vẫn không để mô hình quyết

Module này **không hỏi mô hình** câu hỏi nhắc tới tỉnh nào. Nó quét tên tỉnh và
tên vùng trong câu bằng bảng danh mục có sẵn — tất định, tra lại được. Sau đó lấy
đơn thật từ database và dựng thành một khối chữ.

Mô hình chỉ nhận khối chữ đó như một nguồn nữa trong ngữ cảnh, và diễn đạt lại.
Mọi mã đơn, tên tỉnh và yêu cầu trong câu trả lời vì thế đều là dữ liệu có thật —
đúng ràng buộc R1 và R3 trong `docs/design/11`.

## Chỉ đơn công khai

Dùng `job_orders.public_filter`: đã bật công khai, đang tuyển, còn hạn nộp. Đơn
nháp hoặc đã đóng không được lọt ra ngoài qua đường chat — cùng một quy tắc với
trang danh mục trên website, và dùng chung đúng một hàm để hai nơi không lệch.
"""
from typing import Any

from app.db import job_orders as store
from app.matching import catalog
from app.rag.taxonomy import normalize_text


# Nhiều đơn quá thì khối chữ dài, lấn chỗ của tài liệu chính sách trong prompt.
# Năm đơn đủ để trả lời "có đơn nào ở đó không" và kể ra vài cái tên.
MAX_ORDERS = 5


def _tokens(text: str) -> list[str]:
    import re

    return re.findall(r"[a-z0-9]+", normalize_text(text))


def _find(tokens: list[str], lookup: dict[str, str]) -> str | None:
    """Tìm tên dài nhất trong bảng tra xuất hiện liền mạch trong câu.

    Tìm tên dài trước: "hokkaido do" phải thắng "hokkaido", và tên hai tiếng như
    "tokyo to" không bị cắt còn một nửa.
    """
    for length in (3, 2, 1):
        for start in range(len(tokens) - length + 1):
            cum = " ".join(tokens[start : start + length])
            if cum in lookup:
                return lookup[cum]
    return None


def detect_location(query: str) -> tuple[str | None, str | None]:
    """Câu hỏi có nhắc tới tỉnh hoặc vùng nào không.

    Trả về `(tỉnh, vùng)`. Nhắc tỉnh thì suy ra luôn vùng chứa tỉnh đó, để còn
    gợi ý đơn lân cận khi chính tỉnh ấy không có đơn nào.
    """
    tokens = _tokens(query)
    prefecture = _find(tokens, catalog._PREFECTURE_LOOKUP)
    region = _find(tokens, catalog._REGION_LOOKUP)
    if prefecture and not region:
        region = catalog.region_for_prefecture(prefecture)
    return prefecture, region


async def find_orders(
    prefecture: str | None,
    region: str | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Đơn ở đúng tỉnh, và đơn ở các tỉnh khác cùng vùng.

    Tách làm hai để câu trả lời nói được "Tokyo không có đơn nào, nhưng Saitama
    và Chiba cùng vùng thì có" — hữu ích hơn hẳn một lời từ chối.
    """
    tai_tinh: list[dict[str, Any]] = []
    if prefecture:
        tai_tinh = await store.list_job_orders(
            store.build_query(prefecture=prefecture, only_public=True),
            limit=MAX_ORDERS,
            public=True,
        )

    cung_vung: list[dict[str, Any]] = []
    if region:
        rows = await store.list_job_orders(
            store.build_query(region_group=region, only_public=True),
            limit=MAX_ORDERS + len(tai_tinh),
            public=True,
        )
        cung_vung = [r for r in rows if r.get("prefecture") != prefecture][:MAX_ORDERS]

    return tai_tinh, cung_vung


def _mo_ta(order: dict[str, Any]) -> str:
    req = order.get("requirements") or {}
    phan = [f"{order.get('code')} · {order.get('title', '')}"]
    phan.append(f"nơi làm: {order.get('prefecture')}")
    if req.get("japanese_required"):
        nhan = catalog.JAPANESE_LEVEL_LABELS.get(
            req["japanese_required"], req["japanese_required"]
        )
        phan.append(f"tiếng Nhật từ {nhan}")
    if req.get("age_min") and req.get("age_max"):
        phan.append(f"tuổi {req['age_min']}–{req['age_max']}")
    if order.get("deadline"):
        phan.append(f"hạn nộp {order['deadline']}")
    return "  - " + " · ".join(phan)


def render_block(
    prefecture: str | None,
    region: str | None,
    tai_tinh: list[dict[str, Any]],
    cung_vung: list[dict[str, Any]],
) -> str:
    """Khối chữ đưa vào ngữ cảnh. Sinh hoàn toàn bằng mã, không qua mô hình."""
    if not prefecture and not region:
        return ""

    ten = prefecture or catalog.REGION_LABELS.get(region, region)
    dong = [f"[Danh mục đơn đang tuyển — {ten}]"]

    if tai_tinh:
        dong.append(f"Hiện có {len(tai_tinh)} đơn đang tuyển tại {prefecture}:")
        dong.extend(_mo_ta(order) for order in tai_tinh)
    elif prefecture:
        dong.append(f"Hiện KHÔNG có đơn nào đang tuyển tại {prefecture}.")

    if cung_vung:
        nhan_vung = catalog.REGION_LABELS.get(region, region)
        # Chỉ gọi là "đơn khác" khi có một tỉnh cụ thể để mà khác. Hỏi thẳng theo
        # vùng thì đây là toàn bộ danh sách, không phải phần còn lại của cái gì.
        dong.append(
            f"Các đơn khác cùng vùng {nhan_vung}:"
            if prefecture
            else f"Các đơn đang tuyển ở vùng {nhan_vung}:"
        )
        dong.extend(_mo_ta(order) for order in cung_vung)

    if not tai_tinh and not cung_vung:
        dong.append("Không có đơn nào đang tuyển ở khu vực này.")

    # Nói thẳng ràng buộc nghiệp vụ để mô hình không tự suy ra điều ngược lại.
    dong.append(
        "(Nơi làm việc do từng đơn hàng quy định, không phụ thuộc nơi học tiếng. "
        "Danh sách này chỉ gồm đơn đang tuyển và còn hạn nộp.)"
    )
    return "\n".join(dong)


async def context_for(query: str) -> str:
    """Toàn bộ việc: dò địa điểm, tra đơn, dựng khối chữ. Rỗng nếu không nhắc địa điểm."""
    prefecture, region = detect_location(query)
    if not prefecture and not region:
        return ""
    tai_tinh, cung_vung = await find_orders(prefecture, region)
    return render_block(prefecture, region, tai_tinh, cung_vung)
