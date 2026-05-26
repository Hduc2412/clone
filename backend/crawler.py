import requests 
from bs4 import BeautifulSoup
import json
import os

WEBSITE_SECTIONS = {
    "cong_ty": {
        "url": "https://xklddieuduong.vn/",
        "keywords": ["công ty", "dc", "trung tâm", "giới thiệu", "về công ty"],
        "title": "Công ty DC Trung tâm học"
    },
    "don_hang": {
        "url": "https://xklddieuduong.vn/?product_cat=don-hang",
        "keywords": ["đơn hàng", "hỏi đáp", "điều dưỡng", "hộ lý", "câu hỏi"],
        "title": "Hỏi đáp về điều dưỡng"
    },
    "chi_phi": {
        "url": "https://xklddieuduong.vn/?product_cat=quy-trinh-chi-phi-don",
        "keywords": ["chi phí", "phí", "tiền", "đóng bao nhiêu", "mất bao nhiêu", "quy trình"],
        "title": "Quy trình và chi phí đơn"
    },
    "dang_ky": {
        "url": "https://xklddieuduong.vn/?product_cat=dang-ky-don",
        "keywords": ["đăng ký", "thủ tục", "các bước", "đăng ký đơn"],
        "title": "Đăng ký đơn"
    },
    "phong_van": {
        "url": "https://xklddieuduong.vn/?product_cat=phong-van-va-nhap-hoc",
        "keywords": ["phỏng vấn", "nhập học", "thi", "học tiếng nhật"],
        "title": "Phỏng vấn và nhập học"
    },
    "lop_hoc": {
        "url": "https://xklddieuduong.vn/?product_cat=lop-hoc-ki-tuc-xa",
        "keywords": ["lớp học", "ký túc xá", "học", "ở đâu", "chỗ ở"],
        "title": "Lớp học và ký túc xá"
    },
    "xuat_canh": {
        "url": "https://xklddieuduong.vn/?product_cat=hoc-vien-xuat-canh",
        "keywords": ["xuất cảnh", "bay", "sang nhật", "khởi hành", "học viên xuất cảnh"],
        "title": "Học viên xuất cảnh"
    },
    "tai_nhat": {
        "url": "https://xklddieuduong.vn/?product_cat=hoc-vien-tai-nhat",
        "keywords": ["tại nhật", "đang ở nhật", "học viên nhật", "làm việc nhật"],
        "title": "Học viên tại Nhật"
    }
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


# HÀM LẤY BÀI VIẾT TỪ MỘT MỤC 

def get_posts_from_section(section_url: str) -> list:
    try:
        response = requests.get(section_url, headers=HEADERS, timeout=10)
        response.encoding = "utf-8"
        soup = BeautifulSoup(response.text, "html.parser")

        posts = []
        seen_urls = set() #Lưu URL đã trùng

        # Dùng class "product-small col" thay vì "product"
        products = soup.find_all("div", class_="product-small")

        for product in products:
            # Lấy link bài viết
            link = product.find("a", class_="woocommerce-LoopProduct-link")
            url = link.get("href") if link else None
            if url in seen_urls:
                continue # Bỏ qua nếu URL đã thấy
            seen_urls.add(url)
            # Lấy tên bài viết
            title_tag = product.find("a", class_="woocommerce-LoopProduct-link")
            title = title_tag.get_text(strip=True) if title_tag else ""

            # Lấy ảnh — dùng data-src vì website dùng lazy load
            img = product.find("img")
            image = img.get("data-src") if img else None

            # Lấy ảnh chất lượng cao từ data-srcset
            if img and img.get("data-srcset"):
                srcset = img.get("data-srcset")
                # Lấy link ảnh lớn nhất (768w)
                for src in srcset.split(","):
                    if "768" in src:
                        image = src.strip().split(" ")[0]
                        break

            if url:
                posts.append({
                    "title": title,
                    "url": url,
                    "image": image
                })

        print(f"Tìm thấy {len(posts)} bài viết")
        return posts

    except Exception as e:
        print(f"Lỗi: {e}")
        return []
    
# Tìm mục phù hợp dựa trên từ khóa trong câu hỏi để trả về của mục đó
def find_section_by_keyword(question: str) -> str:
    """Tìm mục phù hợp dựa trên từ khóa trong câu hỏi
    Trả về: key của mục trong WEBSITE_SECTIONS hoặc None"""
    question_lower = question.lower()

    for section_key, section_data in WEBSITE_SECTIONS.items():
        for keyword in section_data["keywords"]:
            if keyword in question_lower:
                print(f"Tìm thấy mục: {section_data['title']}")
                return section_key

    print("Không tìm thấy mục phù hợp")
    return None

# Nhận câu hỏi trả về bài viết phù hợp
def get_section_content(question: str) -> dict:
    """
    Hàm chính — nhận câu hỏi, trả về danh sách bài viết + ảnh phù hợp
    Được gọi từ gemini_service.py
    """
    # Bước 1: Tìm mục phù hợp
    section_key = find_section_by_keyword(question)

    if not section_key:
        return {
            "section": None,
            "title": "",
            "posts": []
        }

    section = WEBSITE_SECTIONS[section_key]

    # Bước 2: Crawl danh sách bài viết trong mục đó
    posts = get_posts_from_section(section["url"])

    return {
        "section": section_key,
        "title": section["title"],
        "posts": posts
    }

if __name__ == "__main__":
    # Test tìm kiếm theo câu hỏi
    question = "Chi phí đi Nhật là bao nhiêu?"
    result = get_section_content(question)

    print(f"\nMục: {result['title']}")
    print(f"Số bài viết: {len(result['posts'])}")
    for post in result["posts"]:
        print("---")
        print("Tên:", post["title"])
        print("Link:", post["url"])
        print("Ảnh:", post["image"])