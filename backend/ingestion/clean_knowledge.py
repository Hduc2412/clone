# -*- coding: utf-8 -*-
"""Làm sạch phần chữ đọc từ ảnh đang lưu trong Qdrant.

Toàn bộ tri thức của hệ thống nằm trong ảnh trên website, nên chất lượng phần
chữ đọc ra chính là chất lượng câu trả lời. Ba loại rác đang lẫn vào:

1. **Số điện thoại sai.** Mô hình đọc watermark mờ và nuốt mất cụm giữa, thành
   `0971. 939`. Dạng sai này xuất hiện nhiều hơn dạng đúng, và bộ kiểm chứng
   không chặn được vì nó chỉ bắt chuỗi 10–11 chữ số.
2. **Câu dẫn nhập của mô hình.** "Dưới đây là toàn bộ nội dung text trong ảnh:"
   và các biến thể — lời của máy, không phải nội dung tài liệu.
3. **Vụn điều hướng của website.** Mỗi đoạn đều mở đầu bằng breadcrumb và
   "Giá: liên hệ", lặp lại y hệt ở cả 32 đoạn nên chỉ làm loãng vector.

Chạy `--preview` để xem trước, không đổi gì. Chạy `--write` để ghi sang
collection staging; alias chỉ đổi thủ công sau khi đã kiểm tra.
"""
import argparse
import re

from qdrant_client import QdrantClient, models

from app.core.config import settings
from app.conversation.fallback_messages import SUPPORT_PHONE

SOURCE = "xkld_knowledge"
STAGING = "xkld_knowledge_staging"

IMAGE_MARKER = "[NỘI DUNG TỪ ẢNH]"

# Dạng số bị đọc sót cụm giữa. Chỉ sửa đúng dạng này, không đụng chuỗi số khác.
BROKEN_PHONE = re.compile(r"0971\.\s*939")

# Vụn điều hướng ở đầu mỗi đoạn: "Trang chủ / <chuyên mục> <tiêu đề> Giá: liên hệ".
BREADCRUMB = re.compile(r"^\s*Trang chủ\s*/.*?Giá:\s*liên hệ\s*", re.S)

# Câu dẫn nhập của mô hình, luôn đứng ngay sau dấu mốc và luôn kết thúc bằng ":".
PREAMBLE = re.compile(
    r"^\s*(?:Chắc chắn rồi[,.]?\s*)?"
    r"(?:Chào bạn[,.]?\s*)?"
    r"(?:(?:tôi đã đọc|Tôi đã đọc|Dựa trên|Dưới đây là|Nội dung)[^:\n]{0,140}:)"
    r"\s*(?:-{2,}\s*)?",
)


def clean_text(text: str) -> str:
    """Trả về phần chữ đã bỏ rác, giữ nguyên nội dung thật của tài liệu."""
    text = BROKEN_PHONE.sub(SUPPORT_PHONE, text)
    text = BREADCRUMB.sub("", text)

    if IMAGE_MARKER in text:
        head, _, tail = text.partition(IMAGE_MARKER)
        tail = PREAMBLE.sub("", tail, count=1)
        text = f"{head.strip()}\n{IMAGE_MARKER}\n{tail.strip()}".strip()

    # Gộp dòng trống thừa sinh ra sau khi cắt.
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def load_points(client: QdrantClient) -> list:
    points, _ = client.scroll(
        SOURCE, limit=1000, with_payload=True, with_vectors=True
    )
    return points


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true",
                        help="ghi kết quả sang collection staging")
    parser.add_argument("--reembed", action="store_true",
                        help="nhúng lại vector từ phần chữ đã làm sạch")
    args = parser.parse_args()

    client = QdrantClient(url=settings.qdrant_url)
    points = load_points(client)
    print(f"Đọc {len(points)} đoạn từ '{SOURCE}'.\n")

    changed, phone_fixed, shrunk = 0, 0, 0
    cleaned: list[tuple] = []
    for p in points:
        before = p.payload.get("text", "")
        after = clean_text(before)
        if after != before:
            changed += 1
            shrunk += len(before) - len(after)
        if BROKEN_PHONE.search(before):
            phone_fixed += len(BROKEN_PHONE.findall(before))
        cleaned.append((p, after))

    print(f"Đoạn có thay đổi   : {changed}/{len(points)}")
    print(f"Số chỗ sửa điện thoại: {phone_fixed}")
    print(f"Ký tự rác bỏ đi    : {shrunk:,}")

    if not args.write:
        print("\n--- XEM TRƯỚC 2 đoạn ---")
        for p, after in cleaned[:2]:
            before = p.payload.get("text", "")
            if before == after:
                continue
            print("=" * 74)
            print("BÀI:", p.payload.get("title"))
            print("TRƯỚC:", re.sub(r"\s+", " ", before)[:230])
            print("SAU  :", re.sub(r"\s+", " ", after)[:230])
        print("\nChưa ghi gì. Thêm --write để ghi sang staging.")
        return

    # Ghi sang staging, giữ nguyên vector cũ; bước nhúng lại làm ở script riêng.
    info = client.get_collection(SOURCE)
    if client.collection_exists(STAGING):
        client.delete_collection(STAGING)
    client.create_collection(
        STAGING,
        vectors_config=models.VectorParams(
            size=info.config.params.vectors.size,
            distance=info.config.params.vectors.distance,
        ),
    )
    records = []
    for index, (point, after) in enumerate(cleaned, start=1):
        vector = point.vector
        if args.reembed:
            # Vector cũ được tính trên phần chữ còn rác. Bỏ rác mà giữ vector cũ
            # thì việc truy xuất vẫn bị rác chi phối, nên phải nhúng lại.
            from app.llm.gemini import TASK_DOCUMENT, create_embedding
            from app.rag.indexing import text_for_embedding

            # Đoạn tài liệu phải nhúng kiểu DOCUMENT. Bản trước gọi hàm không
            # truyền tham số nên lấy mặc định là QUERY — cả kho tri thức bị nhúng
            # sai không gian, điểm của đoạn đúng thấp đi chừng 0,06 và tụt hạng.
            #
            # Và phải ghép tiêu đề đúng như lúc thu thập. Bản trước chỉ nhúng
            # thân bài, nên kho có hai loại vector khác nhau nằm lẫn lộn.
            fresh = create_embedding(
                text_for_embedding(point.payload.get("title", ""), after),
                task_type=TASK_DOCUMENT,
            )
            if not fresh:
                raise RuntimeError(
                    f"Nhúng lại thất bại ở đoạn {index}/{len(cleaned)} "
                    f"({point.payload.get('title')}). Dừng để không ghi dở dang."
                )
            vector = fresh
            print(f"  nhúng lại {index}/{len(cleaned)}: {point.payload.get('title','')[:48]}")
        records.append(
            models.PointStruct(id=point.id, vector=vector,
                               payload={**point.payload, "text": after})
        )

    client.upsert(STAGING, points=records)
    print(f"\nĐã ghi {len(records)} đoạn sang '{STAGING}'.")
    if args.reembed:
        print("Vector đã nhúng lại từ phần chữ sạch.")
    else:
        print("Vector vẫn là bản cũ — thêm --reembed trước khi đổi alias.")


if __name__ == "__main__":
    main()
