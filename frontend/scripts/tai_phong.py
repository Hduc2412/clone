"""Tải tệp phông về để tự phục vụ (12/10): build không còn phụ thuộc mạng tới Google.

Đọc CSS Google Fonts đã lưu (bvp.css, gelasio.css), tải từng tệp woff2, ghi CSS mới trỏ về
/fonts/... — giữ nguyên `unicode-range` để trình duyệt chỉ tải bộ chữ cần dùng.
"""
import re
import sys
from pathlib import Path

import httpx

# Chạy: python frontend/scripts/tai_phong.py — cần bvp.css, gelasio.css (CSS Google Fonts tải bằng
# trình duyệt Chrome) đặt cạnh script. Ghi woff2 vào public/fonts của CẢ HAI app và app/phong-chu.css.
GOC = Path(__file__).parent
RA = GOC / "fonts"
RA.mkdir(exist_ok=True)

KHOI = re.compile(r"/\* ([a-z-]+) \*/\s*@font-face \{(.*?)\}", re.S)


def chuyen(css: str, ten_ngan: str) -> str:
    ra = []
    for bo_chu, than in KHOI.findall(css):
        ho = re.search(r"font-family: '([^']+)'", than).group(1)
        kieu = re.search(r"font-style: (\w+)", than).group(1)
        dam = re.search(r"font-weight: (\d+)", than).group(1)
        url = re.search(r"url\((https://[^)]+\.woff2)\)", than).group(1)
        dai = re.search(r"unicode-range: ([^;]+);", than).group(1)
        tep = f"{ten_ngan}-{dam}{'-italic' if kieu == 'italic' else ''}-{bo_chu}.woff2"
        if not (RA / tep).exists():
            r = httpx.get(url, timeout=30)
            r.raise_for_status()
            (RA / tep).write_bytes(r.content)
        ra.append(
            f"/* {ho} {dam} {kieu} — {bo_chu} */\n@font-face {{\n  font-family: '{ho}';\n  font-style: {kieu};\n"
            f"  font-weight: {dam};\n  font-display: swap;\n  src: url(/fonts/{tep}) format('woff2');\n"
            f"  unicode-range: {dai};\n}}\n"
        )
    return "\n".join(ra)


css = (
    "/* Phông tự phục vụ (12/10) — tải một lần từ Google Fonts, lưu trong repo, để `next build`\n"
    "   không cần mạng. Cả hai phông theo giấy phép SIL Open Font License 1.1 (public/fonts/OFL.txt).\n"
    "   Sinh bằng _tam/phong_tai/tai_phong.py; đừng sửa tay — chạy lại script nếu cần thêm độ đậm. */\n\n"
    + chuyen((GOC / "bvp.css").read_text(encoding="utf-8"), "be-vietnam-pro")
    + "\n"
    + chuyen((GOC / "gelasio.css").read_text(encoding="utf-8"), "gelasio")
    + "\n:root {\n  --font-sans: 'Be Vietnam Pro';\n  --font-serif: 'Gelasio';\n}\n"
)
(GOC / "phong-chu.css").write_text(css, encoding="utf-8")
tong = sum(p.stat().st_size for p in RA.glob("*.woff2"))
print(len(list(RA.glob("*.woff2"))), "tệp,", tong // 1024, "KB")
