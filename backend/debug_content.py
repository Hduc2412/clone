import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; x64) AppleWebKit/537.36"}

#Lay URL bai dau tien
res = requests.get("https://xklddieuduong.vn/?product_cat=don-hang", headers=HEADERS)
res.encoding = "utf-8"
soup = BeautifulSoup(res.text, "html.parser")

post = soup.find("div", class_="product-small")
if post:
    link = post.find("a")
    post_url = link.get("href")
    print("URL:", post_url)

    #vao bai viet xem class nao co text
    res2 = requests.get(post_url, headers=HEADERS)
    res2.encoding = "utf-8"
    soup2 = BeautifulSoup(res2.text, "html.parser")

    #In ra tat ca div co class
    for div in soup2.find_all("div", class_=True)[:40]:
        text = div.get_text(strip=True)[:50]
        if text:
            print(f"class={div.get('class')} | text={text}")