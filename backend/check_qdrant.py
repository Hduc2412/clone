"""Kiểm tra cấu trúc và mức độ hoàn chỉnh của dữ liệu Qdrant."""

import argparse
import os
import sys
from collections import Counter

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import ResponseHandlingException


DEFAULT_COLLECTION = "xkld_knowledge"
REQUIRED_PAYLOAD_FIELDS = {
    "text",
    "title",
    "url",
    "section",
    "section_title",
    "topic",
    "chunk_index",
}
IMAGE_CONTENT_MARKER = "[NỘI DUNG TỪ ẢNH]"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Kiểm tra dữ liệu collection Qdrant mà không thay đổi dữ liệu."
    )
    parser.add_argument(
        "--collection",
        default=os.getenv("QDRANT_COLLECTION_NAME", DEFAULT_COLLECTION),
        help="Tên collection cần kiểm tra.",
    )
    parser.add_argument(
        "--require-image-content",
        action="store_true",
        help="Báo lỗi nếu collection không có chunk chứa nội dung đọc từ ảnh.",
    )
    parser.add_argument(
        "--require-complete-images",
        action="store_true",
        help="Báo lỗi nếu có URL có ảnh nhưng chưa có nội dung đọc từ ảnh.",
    )
    return parser.parse_args()


def read_all_points(client: QdrantClient, collection_name: str) -> list:
    points = []
    offset = None

    while True:
        batch, offset = client.scroll(
            collection_name=collection_name,
            limit=100,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        points.extend(batch)
        if offset is None:
            return points


def audit_collection(
    client: QdrantClient,
    collection_name: str,
    require_image_content: bool,
    require_complete_images: bool,
) -> int:
    collection_names = {
        item.name for item in client.get_collections().collections
    }
    aliases = {
        item.alias_name: item.collection_name
        for item in client.get_aliases().aliases
    }
    if collection_name not in collection_names and collection_name not in aliases:
        print(f"FAIL: Collection '{collection_name}' không tồn tại.")
        return 1
    if collection_name in aliases:
        print(
            f"Alias: {collection_name} -> {aliases[collection_name]}"
        )

    points = read_all_points(client, collection_name)
    section_counts = Counter()
    topic_counts = Counter()
    urls = set()
    titles = set()
    missing_fields = Counter()
    image_content_chunks = 0
    urls_with_images = set()
    urls_with_image_content = set()
    incomplete_chunks = 0
    staging_collection = collection_name.endswith("_staging")

    for point in points:
        payload = point.payload or {}
        section_counts[payload.get("section", "<thiếu section>")] += 1
        topic_counts[payload.get("topic", "<thiếu topic>")] += 1

        if payload.get("url"):
            urls.add(payload["url"])
            if payload.get("image"):
                urls_with_images.add(payload["url"])
        if payload.get("title"):
            titles.add(payload["title"])

        for field in REQUIRED_PAYLOAD_FIELDS:
            if payload.get(field) in (None, ""):
                missing_fields[field] += 1

        if IMAGE_CONTENT_MARKER in payload.get("text", ""):
            image_content_chunks += 1
            if payload.get("url"):
                urls_with_image_content.add(payload["url"])

        if staging_collection and payload.get("ingestion_complete") is not True:
            incomplete_chunks += 1

    print(f"Collection: {collection_name}")
    print(f"Tổng chunks: {len(points)}")
    print(f"Số URL duy nhất: {len(urls)}")
    print(f"Số tiêu đề duy nhất: {len(titles)}")
    print(f"Chunks có nội dung từ ảnh: {image_content_chunks}")
    missing_image_urls = urls_with_images - urls_with_image_content
    print(f"URL có ảnh nhưng chưa đọc được ảnh: {len(missing_image_urls)}")
    print("Chunks theo section:")
    for section, count in sorted(section_counts.items()):
        print(f"  - {section}: {count}")
    print("Chunks theo topic:")
    for topic, count in sorted(topic_counts.items()):
        print(f"  - {topic}: {count}")

    errors = []
    if not points:
        errors.append("collection chưa có dữ liệu")
    if missing_fields:
        details = ", ".join(
            f"{field}={count}" for field, count in sorted(missing_fields.items())
        )
        errors.append(f"thiếu payload bắt buộc: {details}")
    if incomplete_chunks:
        errors.append(
            f"{incomplete_chunks} chunks staging chưa được đánh dấu hoàn tất"
        )
    if require_image_content and image_content_chunks == 0:
        errors.append("không có chunk chứa nội dung đọc từ ảnh")
    if require_complete_images and missing_image_urls:
        errors.append(
            f"{len(missing_image_urls)} URL có ảnh nhưng chưa có nội dung ảnh"
        )

    if errors:
        print("KẾT QUẢ: FAIL")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("KẾT QUẢ: PASS")
    return 0


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    load_dotenv()
    args = parse_args()
    client = QdrantClient(
        url=os.getenv("QDRANT_URL", "http://localhost:6333"),
        timeout=10,
    )

    try:
        return audit_collection(
            client,
            args.collection,
            args.require_image_content,
            args.require_complete_images,
        )
    except ResponseHandlingException as exc:
        print(f"FAIL: Không kết nối được Qdrant: {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
