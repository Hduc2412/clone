# ============================================================
# FILE: ingestion/embedder.py
# Nhiệm vụ: Crawl website → đọc ảnh → chunk → embedding → lưu Qdrant
# Chạy 1 lần để build knowledge base
# ============================================================

import os
import re 
import sys
import time
import uuid
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from pathlib import Path
from google import genai
from google.genai import types
from qdrant_client import QdrantClient, models
from qdrant_client.models import Distance, VectorParams, PointStruct

# Fix path .env — tìm từ thư mục gốc project
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

# Import từ đúng path sau khi migrate
from ingestion.image_reader import read_image_content, get_best_image_url
from app.rag.taxonomy import infer_topic, normalize_text

# ============================================================
# CẤU HÌNH
# ============================================================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")  # Fix lỗi 1
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "xkld_knowledge")
BUILD_COLLECTION_NAME = os.getenv(
    "QDRANT_BUILD_COLLECTION_NAME",
    f"{COLLECTION_NAME}_staging",
)
RESET_BUILD_COLLECTION = os.getenv(
    "RESET_BUILD_COLLECTION",
    "false",
).lower() in {"1", "true", "yes"}
EMBEDDING_MODEL = "gemini-embedding-001"
VECTOR_SIZE = 3072
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
EMBEDDING_DELAY_SECONDS = float(os.getenv("EMBEDDING_DELAY_SECONDS", "3"))
POST_DELAY_SECONDS = float(os.getenv("POST_DELAY_SECONDS", "3"))

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

WEBSITE_SECTIONS = {
    "chi_phi": {
        "url": "https://xklddieuduong.vn/?product_cat=quy-trinh-chi-phi-don",
        "title": "Chi phí đơn điều dưỡng",
        "filter_keywords": ["chi phí", "đóng phí", "tiền", "phí"],  # chỉ lấy bài có keyword này trong title
    },
    "quy_trinh": {
        "url": "https://xklddieuduong.vn/?product_cat=quy-trinh-chi-phi-don",
        "title": "Quy trình đi Nhật",
        "filter_keywords": ["quy trình", "vấn đề", "các bước", "thủ tục"],
    },
    "don_hang": {
        "url": "https://xklddieuduong.vn/?product_cat=don-hang",
        "title": "Hỏi đáp về điều dưỡng",
        "filter_keywords": [],  # lấy hết
    },
    "lop_hoc": {
        "url": "https://xklddieuduong.vn/?product_cat=lop-hoc-ki-tuc-xa",
        "title": "Lớp học và ký túc xá",
        "filter_keywords": [],  # lấy hết
    },
}

# ============================================================
# BƯỚC 1: CRAWL
# ============================================================
def get_posts_from_section(section_url: str) -> list:
    """Lấy danh sách URL + title + image của tất cả bài viết trong 1 section"""
    try:
        res = requests.get(section_url, headers=HEADERS, timeout=10)
        res.encoding = "utf-8"
        soup = BeautifulSoup(res.text, "html.parser")

        posts = []
        seen_urls = set()

        for product in soup.find_all("div", class_="product-small"):
            link = product.find("a", class_="woocommerce-LoopProduct-link")
            url = link.get("href") if link else None

            if not url or url in seen_urls:
                continue
            seen_urls.add(url)

            title = link.get_text(strip=True) if link else ""

            img = product.find("img")
            image = img.get("data-src") if img else None
            if img and img.get("data-srcset"):
                for src in img.get("data-srcset").split(","):
                    if "768" in src:
                        image = src.strip().split(" ")[0]
                        break

            posts.append({"title": title, "url": url, "image": image})

        return posts

    except Exception as e:
        print(f"Lỗi crawl section: {e}")
        return []


def get_post_content(post_url: str) -> tuple:
    """Lấy nội dung text + soup của 1 bài viết"""
    try:
        res = requests.get(post_url, headers=HEADERS, timeout=10)
        res.encoding = "utf-8"
        soup = BeautifulSoup(res.text, "html.parser")

        content = (
            soup.find("div", class_="entry-summary") or
            soup.find("div", class_="product-info") or
            soup.find("div", class_="summary") or
            soup.find("div", class_="entry-content") or
            soup.find("article")
        )

        if content:
            for tag in content.find_all(["script", "style"]):
                tag.decompose()
            raw_text = content.get_text(separator=" ", strip=True)
            return clean_text(raw_text), content

        return "", None

    except Exception as e:
        print(f"Lỗi đọc bài viết: {e}")
        return "", None


# ============================================================
# BƯỚC 2: CHUNK
# ============================================================
def split_into_chunks(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list:
    """Chia text thành các chunk nhỏ theo từ, có overlap"""
    words = text.split()
    if not words:
        return []

    chunks = []
    start = 0

    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start += chunk_size - overlap

    return chunks


# ============================================================
# BƯỚC 3: EMBEDDING
# ============================================================
def create_embedding(client: genai.Client, text: str) -> list:
    """Tạo vector embedding cho 1 đoạn text bằng Gemini"""
    try:
        result = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=text,
            config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
        )
        return result.embeddings[0].values
    except Exception as e:
        print(f"Lỗi tạo embedding: {e}")
        return None


# ============================================================
# BƯỚC 4: LƯU VÀO QDRANT
# ============================================================
def setup_build_collection(qdrant: QdrantClient) -> None:
    """Tạo hoặc tiếp tục collection staging, không thay đổi collection chính."""
    existing = [c.name for c in qdrant.get_collections().collections]

    if BUILD_COLLECTION_NAME in existing and RESET_BUILD_COLLECTION:
        print(f"Xóa collection staging cũ: '{BUILD_COLLECTION_NAME}'")
        qdrant.delete_collection(BUILD_COLLECTION_NAME)
        existing.remove(BUILD_COLLECTION_NAME)

    if BUILD_COLLECTION_NAME not in existing:
        qdrant.create_collection(
            collection_name=BUILD_COLLECTION_NAME,
            vectors_config=VectorParams(
                size=VECTOR_SIZE,
                distance=Distance.COSINE
            )
        )
        print(f"Đã tạo collection staging '{BUILD_COLLECTION_NAME}'")
    else:
        print(f"Tiếp tục collection staging '{BUILD_COLLECTION_NAME}'")


def is_post_complete(qdrant: QdrantClient, post: dict) -> bool:
    """Kiểm tra cả phần chữ và phần ảnh của bài đã hoàn tất chưa."""
    existing, _ = qdrant.scroll(
        collection_name=BUILD_COLLECTION_NAME,
        scroll_filter=models.Filter(
            must=[
                models.FieldCondition(
                    key="url",
                    match=models.MatchValue(value=post["url"]),
                ),
                models.FieldCondition(
                    key="ingestion_complete",
                    match=models.MatchValue(value=True),
                ),
            ]
        ),
        limit=100,
        with_payload=True,
        with_vectors=False,
    )
    if not existing:
        return False

    if not post.get("image"):
        return True

    return any(
        "[NỘI DUNG TỪ ẢNH]" in (point.payload or {}).get("text", "")
        for point in existing
    )


def make_point_id(post_url: str, chunk_index: int) -> str:
    """Tạo ID ổn định để chạy lại không sinh bản ghi trùng."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{post_url}#chunk-{chunk_index}"))


# ============================================================
# HÀM CHÍNH
# ============================================================
def run_embedding_pipeline():
    """Pipeline chính: crawl → chunk → embed → lưu Qdrant"""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    print("=" * 50)
    print("BẮT ĐẦU EMBEDDING PIPELINE")
    print("=" * 50)

    if not GEMINI_API_KEY:
        raise RuntimeError("Thiếu GEMINI_API_KEY trong file .env")

    if BUILD_COLLECTION_NAME == COLLECTION_NAME:
        raise RuntimeError(
            "Collection staging phải khác collection chính để bảo vệ dữ liệu."
        )

    # Kết nối
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    qdrant = QdrantClient(url=QDRANT_URL)
    print("Đã kết nối Gemini và Qdrant")

    # Chỉ làm việc với collection staging; collection chính luôn được giữ nguyên.
    setup_build_collection(qdrant)

    total_chunks = 0
    completed_posts = 0
    failed_posts = 0

    for section_key, section_info in WEBSITE_SECTIONS.items():
        print(f"\n[{section_key.upper()}] {section_info['title']}")  
        print(f"  Crawl: {section_info['url']}")

        posts = get_posts_from_section(section_info["url"])
        filter_keywords = section_info.get("filter_keywords", [])
        if filter_keywords:
            posts = [
                p for p in posts
                if any(
                    normalize_text(keyword) in normalize_text(p["title"])
                    for keyword in filter_keywords
                )
            ]

        print(f"  Tìm thấy {len(posts)} bài viết sau filter")

        for post in posts:
            print(f"  → {post['title'][:50]}...")

            if is_post_complete(qdrant, post):
                print("    Bài đã hoàn tất trong staging, bỏ qua")
                continue

            # Lấy nội dung text
            text, soup = get_post_content(post["url"])
            if not text and not soup:
                continue

            # Fix lỗi 4 — chỉ đọc ảnh thumbnail 1 lần
            if soup and post.get("image"):
                best_url = get_best_image_url(post["image"])
                print(f"    Đọc ảnh: {best_url[:60]}...")
                image_text = read_image_content(
                    best_url,
                    "Hãy đọc toàn bộ nội dung text trong ảnh này"
                )
                if image_text:
                    text = text + "\n\n[NỘI DUNG TỪ ẢNH]\n" + clean_text(image_text)
                    print(f"    Đã extract text từ ảnh")
                else:
                    failed_posts += 1
                    print(
                        "    Tạm hoãn bài vì chưa đọc được ảnh; "
                        "sẽ thử lại ở lần chạy sau."
                    )
                    time.sleep(POST_DELAY_SECONDS)
                    continue

            image_content_included = "[NỘI DUNG TỪ ẢNH]" in text

            # Chunk
            chunks = split_into_chunks(text)
            print(f"    Chia thành {len(chunks)} chunks")

            # Embed + lưu
            points = []
            post_failed = False
            for i, chunk in enumerate(chunks):
                enriched_chunk = f"{post['title']}\n{chunk}"
                vector = create_embedding(gemini_client, enriched_chunk)
                if not vector:
                    post_failed = True
                    print(
                        "    Dừng bài hiện tại vì một chunk embedding thất bại; "
                        "chưa ghi dữ liệu dở dang."
                    )
                    break

                points.append(PointStruct(
                    id=make_point_id(post["url"], i),
                    vector=vector,
                    payload={
                        "text": chunk,
                        "title": post["title"],
                        "url": post["url"],
                        "image": post["image"],
                        "section": section_key,
                        "section_title": section_info["title"],
                        "topic": infer_topic(section_key, post["title"]),
                        "chunk_index": i,
                        "chunk_count": len(chunks),
                        "ingestion_complete": True,
                        "image_content_included": image_content_included,
                    }
                ))
                time.sleep(EMBEDDING_DELAY_SECONDS)

            if not post_failed and points and len(points) == len(chunks):
                qdrant.upsert(
                    collection_name=BUILD_COLLECTION_NAME,
                    points=points,
                )
                total_chunks += len(points)
                completed_posts += 1
                print(f"    Đã lưu {len(points)} vectors vào Qdrant")
            else:
                failed_posts += 1

            time.sleep(POST_DELAY_SECONDS)

    print("\n" + "=" * 50)
    print(f"HOÀN TẤT! Đã lưu mới {total_chunks} chunks")
    print(f"Số bài hoàn tất trong lần chạy này: {completed_posts}")
    print(f"Số bài thất bại trong lần chạy này: {failed_posts}")
    print(f"Collection staging: '{BUILD_COLLECTION_NAME}'")
    print(f"Collection chính chưa thay đổi: '{COLLECTION_NAME}'")
    print("=" * 50)

def clean_text(text: str) -> str:
    """Làm sạch text crawl trước khi chunk + embed"""
    # Thay &nbsp; và các HTML entities còn sót
    text = text.replace("\xa0", " ").replace("&nbsp;", " ")
    
    # Xóa nhiều khoảng trắng/xuống dòng liên tiếp
    text = re.sub(r"\s+", " ", text)
    
    # Xóa các dòng quá ngắn (< 15 ký tự) — thường là menu/label thừa
    lines = [line.strip() for line in text.split(".") if len(line.strip()) >= 15]
    text = ". ".join(lines)
    
    return text.strip()

if __name__ == "__main__":
    run_embedding_pipeline()
