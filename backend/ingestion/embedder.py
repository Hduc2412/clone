# Crawl toàn bộ website → đọc nội dung text từng bài viết
#          → chia chunk → tạo vector bằng Gemini → lưu vào Qdrant
import os
import time
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from google import genai
from google.genai import types
from qdrant_client import QdrantClient, models
from qdrant_client.models import Distance, VectorParams, PointStruct
from image_reader import read_image_content
from image_reader import read_image_content, get_best_image_url

load_dotenv()

# Cấu hình

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
QDRANT_URL = os.getenv("http://localhost:6333")
COLLECTION_NAME = "xkld_knowledge"
EMBEDDING_MODEL = "gemini-embedding-001"
VECTOR_SIZE = 3072  # Kích thước vector của text-embedding-001
CHUNK_SIZE = 500 # Số ký tự mỗi chunk
CHUNK_OVERLAP = 50 # Số ký tự chồng lấn giữa các chunk

HEADERS = {
    "User-Agent" : "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# Tất cả section cần crawl - tái sử dụng từ crawler.py
WEBSITE_SECTIONS = {
    "cong_ty": {
        "url": "https://xklddieuduong.vn/",
        "title": "Công ty DC Trung tâm học"
    },
    "don_hang": {
        "url": "https://xklddieuduong.vn/?product_cat=don-hang",
        "title": "Hỏi đáp về điều dưỡng"
    },
    "chi_phi": {
        "url": "https://xklddieuduong.vn/?product_cat=quy-trinh-chi-phi-don",
        "title": "Quy trình và chi phí đơn"
    },
    "dang_ky": {
        "url": "https://xklddieuduong.vn/?product_cat=dang-ky-don",
        "title": "Đăng ký đơn"
    },
    "phong_van": {
        "url": "https://xklddieuduong.vn/?product_cat=phong-van-va-nhap-hoc",
        "title": "Phỏng vấn và nhập học"
    },
    "lop_hoc": {
        "url": "https://xklddieuduong.vn/?product_cat=lop-hoc-ki-tuc-xa",
        "title": "Lớp học và ký túc xá"
    },
    "xuat_canh": {
        "url": "https://xklddieuduong.vn/?product_cat=hoc-vien-xuat-canh",
        "title": "Học viên xuất cảnh"
    },
    "tai_nhat": {
        "url": "https://xklddieuduong.vn/?product_cat=hoc-vien-tai-nhat",
        "title": "Học viên tại Nhật"
    }
}
#=== Bước 1: CRAWL====
def get_post_url_from_section(section_url: str) -> list:
    """Lấy danh sách URL + title + image của tất cả bài viết trong 1 section"""
    try:
        res = requests.get(section_url, headers=HEADERS, timeout=10)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')

        posts = []
        seen_urls = set() # Dùng set để tránh trùng lặp URL

        for product in soup.find_all("div", class_="product"):
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
        print(f" Loi crawl section: {e}")
        return []
def get_post_content(post_url: str) -> tuple:
    """Trả về (text, soup) để dùng tiếp cho image extraction"""
    try:
        res = requests.get(post_url, headers=HEADERS, timeout=10)
        res.encoding = "utf-8"
        soup = BeautifulSoup(res.text, 'html.parser')

        # Thử lấy nội dung từ các class phổ biến của WooCommerce/WordPress
        content = (
            soup.find("div", class_="entry-summary") or
            soup.find("div", class_="product-info") or
            soup.find("div", class_="summary") or
            soup.find("div", class_="entry-content") or
            soup.find("article")
        )

        if content:
            # Xóa script và style rác
            for tag in content.find_all(["script", "style"]):
                tag.decompose()
            return content.get_text(separator=" ", strip=True), content
 
        return "", None
    except Exception as e:
        print(f"  Lỗi đọc bài viết: {e}")
        return "", None

def extract_text_from_images(soup) -> str:
    """
    Tìm tất cả ảnh trong bài viết → dùng Gemini Vision đọc nội dung
    """
    image_texts = []
    imgs = soup.find_all("img")
    print(f" Tim thay {len(imgs)} anh")
    for img in imgs:
        url = img.get("data-src") or img.get("src") or ""
        print(f" URL anh: {url[:80]}")
        if not url or not url.startswith("http"):
            continue
        #Bo qua anh icon/logo 
        if any(x in url for x in ["logo", "icon", "avatar", "banner"]):
            continue
        best_url = get_best_image_url(url)
        print(f" Doc anh: {url[:60]}...")
        text = read_image_content(url, "Hãy đọc toàn bộ nội dung text trong ảnh này")
        if text and "Khong the" not in text and "Loi" not in text:
            image_texts.append(text)
        time.sleep(1) #tranh ratr limit
    return "\n\n".join(image_texts)

#Bước 2: CHUNK
def split_into_chunks(text: str, chunk_size: int=CHUNK_SIZE, overlap: int= CHUNK_OVERLAP) -> list:
    """
    Chia text thành các chunk nhỏ theo từ
    Có overlap để không mất ngữ cảnh ở ranh giới chunk
    """
    words = text.split()
    if not words:
        return []
    chunks = []
    start = 0

    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        # Bước nhảy = chunk_size - overlap để các chunk kề nhau có phần chung
        start += chunk_size - overlap
    return chunks

# BƯỚC 3: EMBEDDING
def creat_embedding(client: genai.Client, text: str) -> list:
    """Gọi Gemini text-embedding-004 để tạo vector cho 1 đoạn text"""
    try:
        result = client.models.embed_content(
            model=EMBEDDING_MODEL,
             contents=text,
            config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
        )
        return result.embeddings[0].values
    except Exception as e:
        print(f"  Lỗi tạo embedding: {e}")
        return None

# BƯỚC 4: LƯU VÀO QDRANT
def setup_qdrant_collection(qdrant: QdrantClient):
    """Tạo collection mới trong Qdrant, xóa cũ nếu đã tồn tại"""
    existing = [c.name for c in qdrant.get_collections().collections]

    if COLLECTION_NAME in existing:
        print(f"Collection '{COLLECTION_NAME}' đã tồn tại -> xóa và tạo lại")
        qdrant.delete_collection(COLLECTION_NAME)

    qdrant.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=VECTOR_SIZE,
            distance=Distance.COSINE #Cosine similarity phu hop cho text
        )
    )
    print(f"Đã tạo Collection '{COLLECTION_NAME}'")

# HÀM CHÍNH 

def run_embedding_pipeline():
    """
    Pipeline chính:
    1. Kết nối Qdrant + Gemini
    2. Setup collection
    3. Crawl từng section → từng bài viết
    4. Chunk text → tạo vector → lưu Qdrant
    """
    print("=" * 50)
    print("BẮT ĐẦU EMBEDDING PIPELINE")
    print("=" * 50)

    # 1. Kết nối
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    qdrant = QdrantClient(url=QDRANT_URL)
    print("Đã kết nối Gemini\n và Qdrant")

    # 2. Setup collection
    setup_qdrant_collection(qdrant)
    
    total_chunks = 0
    point_id = 0 # ID tăng dần cho từng point trong Qdrant

    # Duyệt qua từng section
    for section_key, section_info in WEBSITE_SECTIONS.items():
        print(f"\n[{section_key.upper()}] {section_info["title"]}")
        print(f" Crawl: {section_info['url']}")

        posts = get_post_url_from_section(section_info["url"])
        print(f"  Tìm thấy {len(posts)} bài viết")

        # Duyệt qua từng bài viết trong section 
        for post in posts:
            print(f" -> {post['title'][:50]}...")
            #check xem URL này đã có trong Qdrant chưa
            existing, _ = qdrant.scroll(
                collection_name=COLLECTION_NAME,
                scroll_filter=models.Filter(
                    must=[models.FieldCondition(
                        key ="url",
                         match=models.MatchValue(value=post["url"])
                    )]
                ),
                limit=1
            )
            if existing:
                print(f"    Đã có trong Qdrant, bỏ qua")
                continue
            # Lấy nội dung text bài viết
            text, soup = get_post_content(post["url"])
            if not text and not soup:
                continue
            if soup:
                print(f" Đọc ảnh trong bài...")
                image_text = extract_text_from_images(soup)
                if post.get("image"):
                    best_url = get_best_image_url(post["image"])
                    print(f"    Đọc ảnh: {best_url[:60]}...")
                    image_text = read_image_content(best_url, "Hãy đọc toàn bộ nội dung text trong ảnh này")
                    if image_text and "Không thể" not in image_text and "Loi" not in image_text:
                        text = text + "\n\n[NỘI DUNG TỪ ẢNH]\n" + image_text
                        print(f"    Đã extract text từ ảnh")
            #Chia chunk
            chunks = split_into_chunks(text)
            print(f"  Chia thành {len(chunks)} chunk")

            # Tạo vector va lưu từng chunk
            points = []
            for i, chunk in enumerate(chunks):
                # Thêm title + đầu chunk để tăng ngữ cảnh khi search
                enriched_chunk = f"{post['title']}\n{chunk}"

                vector = creat_embedding(gemini_client, enriched_chunk)
                if not vector:
                    continue
                
                #Payload = metadata luu vector sau khi sreach
                points.append(PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "text": chunk,           # Text gốc để dùng làm context
                        "title": post["title"],  # Tên bài viết
                        "url": post["url"],      # Link gốc
                        "image": post["image"],  # Ảnh bài viết
                        "section": section_key,  # Mục thuộc về
                        "section_title": section_info["title"],
                        "chunk_index": i         # Vị trí chunk trong bài
                    }
                ))
                point_id += 1
                # Delay nhỏ tránh bị rate limit Gemini API
                time.sleep(0.3)
            # Luu btach vao Qdrant
            if points:
                qdrant.upsert(collection_name=COLLECTION_NAME, points=points)
                total_chunks += len(points)
                print(f"    Đã lưu {len(points)} vectors vào Qdrant")
            
            # Delay giữa các bài viết
            time.sleep(0.5)
    print("\n" + "=" * 50)
    print(f"HOÀN TẤT! Tổng cộng {total_chunks} chunks đã được lưu vào Qdrant.")
    print(f"Collection: '{COLLECTION_NAME}'")
    print("=" * 50)

if __name__ == "__main__":
    run_embedding_pipeline()

      
