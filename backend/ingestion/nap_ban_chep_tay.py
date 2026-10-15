# -*- coding: utf-8 -*-
"""Nạp bản chép tay nội dung ảnh vào kho tri thức, nhúng lại vector.

Nguồn là `Tailieu/TriThuc/NOI_DUNG_ANH_WEBSITE.md` (ngoài repo): người đọc trực tiếp 32 ảnh trên
website ngày 13/10/2026, thay cho bản do mô hình đọc ảnh tự động. Chỉ nhóm A (16
bài có nội dung tư vấn) được nạp; nhóm B là ảnh chụp, ngoài tiêu đề không có chữ,
và `clean_knowledge.py` đã ghi nhận chúng thắng truy hồi rồi trả về một tiêu đề.

Bộ truy hồi không lọc theo chủ đề (xem `app/rag/retriever.py`), nên bỏ nhóm B
không làm chủ đề nào mất đoạn.

Các bước, mỗi bước một lệnh để kiểm được giữa chừng:

    python -m ingestion.nap_ban_chep_tay --xem           # không gọi mô hình
    python -m ingestion.nap_ban_chep_tay --ghi           # 16 lượt nhúng
    python -m ingestion.nap_ban_chep_tay --so-sanh "câu hỏi" ...   # 1 lượt/câu
    python -m ingestion.nap_ban_chep_tay --doi-alias     # không gọi mô hình

Ghi sang collection mới (`DICH`), không đụng collection đang chạy. Alias chỉ đổi khi gọi
`--doi-alias`; lệnh in ra collection cũ để đổi ngược.

**Không có lượt gọi ngầm.** Hàm nhúng mặc định thử lại 3 lần; ở đây khóa còn 1, và
`--tran` chặn tổng số lượt. Lỗi một đoạn thì dừng trước khi tạo collection, để
không bao giờ có một kho nhúng dở.
"""
import argparse
import functools
import hashlib
import json
import re
import time
import uuid
from pathlib import Path

from qdrant_client import QdrantClient, models

from app.core.config import settings
from app.llm import gemini
from app.rag.indexing import text_for_embedding

# Nằm ngoài repo, cạnh tài liệu đồ án: bản chép có địa chỉ văn phòng, mà
# `tests/test_khong_lo_lien_lac.py` không cho địa chỉ nằm trong cây mã.
NGUON = Path(__file__).resolve().parents[3] / "Tailieu" / "TriThuc" / "NOI_DUNG_ANH_WEBSITE.md"
ALIAS = settings.qdrant_collection_name
# Payload gốc (tiêu đề, mục, ảnh) đọc từ bản thu thập 32 đoạn, không qua alias:
# alias đã trỏ sang bản chép tay, mà bản ấy bỏ 16 bài ảnh chụp.
GOC = "xkld_knowledge_v20260917b"
# Mỗi lần nạp một collection mới; collection alias đang trỏ không bao giờ bị xóa.
DICH = "xkld_knowledge_v20261015"
IMAGE_MARKER = "[NỘI DUNG TỪ ẢNH]"
NHAN_NGUON = "chep_tay_20261013"
DEM_VECTOR = Path(__file__).resolve().parents[1] / "data" / "vector_chep_tay.json"
# Giãn các lượt gọi; 429 lần đầu đến sau 10 lượt liền nhau.
GIAN_CACH_GIAY = 4


class HetLuot(RuntimeError):
    pass


def khoa_luot(tran: int) -> list:
    """Một lần thử cho mỗi lượt, và đếm lượt; vượt trần thì dừng."""
    goc = gemini._post_with_retry
    dem = []

    def mot_lan(url, payload, **kw):
        if len(dem) >= tran:
            raise HetLuot(f"Đã dùng hết {tran} lượt được cấp.")
        dem.append(url)
        kw["max_retries"] = 1
        return goc(url, payload, **kw)

    gemini._post_with_retry = functools.wraps(goc)(mot_lan)
    return dem


def noi_dong(doan: str) -> str:
    """Nối dòng bị ngắt theo khổ markdown; giữ xuống dòng ở đầu mục liệt kê."""
    ra: list[str] = []
    for dong in doan.splitlines():
        if ra and not re.match(r"\s*(- |\d+\. )", dong):
            ra[-1] += " " + dong.strip()
        else:
            ra.append(dong.rstrip())
    return "\n".join(ra)


def doc_ban_chep() -> list[dict]:
    """Tách nhóm A thành từng bài: url, ảnh, chủ đề, thân bài."""
    s = NGUON.read_text(encoding="utf-8")
    nhom_a = s.split("## A.", 1)[1].split("\n## B.", 1)[0]
    bai = []
    for khoi in re.split(r"\n### A\d+\. ", nhom_a)[1:]:
        khoi = khoi.split("\n---", 1)[0]
        dong = khoi.splitlines()
        url = re.search(r"^- URL: (\S+)", khoi, re.M).group(1)
        anh = re.search(r"^- Ảnh: (\S+)", khoi, re.M).group(1)
        # Đoạn tổng hợp mượn URL của một bài để có nguồn, nhưng mang tiêu đề riêng.
        tieu_de = re.search(r"^- Tiêu đề: (.+)$", khoi, re.M)
        chu_de = re.search(r"^- Chủ đề: (\S+)", khoi, re.M).group(1)
        than = khoi.split(f"- Chủ đề: {chu_de}", 1)[1]
        # Ghi chú khi chép là lời của người chép, không phải nội dung tài liệu.
        doan = [d.strip() for d in re.split(r"\n\s*\n", than) if d.strip()]
        doan = [noi_dong(d) for d in doan if not d.startswith("Ghi chú khi chép")]
        bai.append({"tieu_de_md": dong[0].strip(), "url": url, "anh": anh,
                    "chu_de": chu_de, "than": "\n\n".join(doan),
                    "tieu_de": tieu_de.group(1).strip() if tieu_de else None})
    return bai


def gop_payload(client: QdrantClient, bai: list[dict]) -> list[tuple]:
    """Giữ payload cũ theo URL (tiêu đề, mục, ảnh…), chỉ thay phần chữ."""
    diem, _ = client.scroll(GOC, limit=200, with_payload=True)
    theo_url = {p.payload.get("url"): p for p in diem}
    ra = []
    for b in bai:
        cu = theo_url.get(b["url"])
        if cu is None:
            raise SystemExit(f"Không thấy bài trong kho đang chạy: {b['url']}")
        payload = {**cu.payload, "text": f"{IMAGE_MARKER}\n{b['than']}",
                   "topic": b["chu_de"], "chunk_index": 0, "chunk_count": 1,
                   "ingestion_complete": True, "nguon_noi_dung": NHAN_NGUON}
        pid = cu.id
        if b["tieu_de"]:
            # Mã riêng để không đè lên bài gốc mang cùng URL; ảnh của bài gốc không
            # thuộc về đoạn tổng hợp.
            pid = str(uuid.uuid5(uuid.NAMESPACE_URL, b["url"] + "#" + b["tieu_de"]))
            payload.update(title=b["tieu_de"], image="")
        ra.append((pid, payload))
    return ra


def _doc_dem() -> dict:
    return json.loads(DEM_VECTOR.read_text(encoding="utf-8")) if DEM_VECTOR.exists() else {}


def ghi(client: QdrantClient, tran: int) -> None:
    diem = gop_payload(client, doc_ban_chep())
    dem = khoa_luot(tran)
    # Vector lấy được lưu xuống đĩa ngay, theo dấu băm của đúng đoạn chữ đem nhúng.
    # Lần chạy đầu ngày 13/10 gặp 429 ở đoạn 11 và vứt mất 10 vector đã trả tiền
    # hạn mức; giờ chạy lại chỉ nhúng phần còn thiếu, và sửa chữ một đoạn thì chỉ
    # đoạn đó phải nhúng lại.
    da_co = _doc_dem()
    ban_ghi, thieu = [], 0
    for i, (pid, payload) in enumerate(diem, 1):
        chu = text_for_embedding(payload.get("title", ""), payload["text"])
        khoa = hashlib.sha256(chu.encode("utf-8")).hexdigest()
        vec = da_co.get(khoa)
        if vec is None:
            if len(dem) >= tran:
                thieu += 1
                continue
            if dem:
                time.sleep(GIAN_CACH_GIAY)
            vec = gemini.create_embedding(chu, task_type=gemini.TASK_DOCUMENT)
            if not vec:
                raise SystemExit(f"Nhúng thất bại ở đoạn {i}/{len(diem)} — dừng, chưa ghi vào Qdrant. "
                                 f"Đã dùng {len(dem)} lượt; {len(da_co)} vector đã lưu ở {DEM_VECTOR.name}.")
            da_co[khoa] = vec
            DEM_VECTOR.write_text(json.dumps(da_co), encoding="utf-8")
            print(f"  nhúng {i}/{len(diem)}: {payload.get('title', '')[:60]}")
        ban_ghi.append(models.PointStruct(id=pid, vector=vec, payload=payload))
    if thieu:
        raise SystemExit(f"Hết {tran} lượt, còn {thieu} đoạn chưa nhúng — chưa ghi vào Qdrant. "
                         f"{len(da_co)} vector đã lưu; chạy lại để nhúng tiếp.")

    cu = client.get_collection(ALIAS).config.params.vectors
    if len(ban_ghi[0].vector) != cu.size:
        raise SystemExit(f"Số chiều lệch: {len(ban_ghi[0].vector)} ≠ {cu.size}")
    dang_tro = {a.collection_name for a in client.get_aliases().aliases if a.alias_name == ALIAS}
    if DICH in dang_tro:
        raise SystemExit(f"'{DICH}' đang được alias '{ALIAS}' trỏ tới — không xóa. Đổi DICH sang tên mới.")
    if client.collection_exists(DICH):
        client.delete_collection(DICH)
    client.create_collection(DICH, vectors_config=models.VectorParams(size=cu.size, distance=cu.distance))
    client.upsert(DICH, points=ban_ghi)
    print(f"\nĐã ghi {len(ban_ghi)} đoạn sang '{DICH}'. Dùng {len(dem)} lượt. Alias chưa đổi.")


def so_sanh(client: QdrantClient, cau_hoi: list[str], tran: int) -> None:
    dem = khoa_luot(tran)
    dang_chay = [a.collection_name for a in client.get_aliases().aliases if a.alias_name == ALIAS][0]
    for q in cau_hoi:
        vec = gemini.create_embedding(q)  # nhúng kiểu QUERY, đúng như bộ truy hồi
        if not vec:
            raise SystemExit(f"Nhúng câu hỏi thất bại — dừng. Đã dùng {len(dem)} lượt.")
        print(f"\nHỎI: {q}")
        for ten in (dang_chay, DICH):
            hits = client.query_points(ten, query=vec, limit=3, with_payload=True).points
            print(f"  [{ten}]")
            for h in hits:
                print(f"     {h.score:.3f}  {h.payload.get('title', '')[:55]}")
    print(f"\nDùng {len(dem)} lượt.")


def doi_alias(client: QdrantClient) -> None:
    cu = [a.collection_name for a in client.get_aliases().aliases if a.alias_name == ALIAS]
    so = client.count(DICH).count
    if so == 0:
        raise SystemExit(f"'{DICH}' rỗng — không đổi.")
    client.update_collection_aliases(change_aliases_operations=[
        models.DeleteAliasOperation(delete_alias=models.DeleteAlias(alias_name=ALIAS)),
        models.CreateAliasOperation(create_alias=models.CreateAlias(collection_name=DICH, alias_name=ALIAS)),
    ])
    print(f"Alias '{ALIAS}': {cu[0] if cu else '(không có)'} → {DICH} ({so} đoạn).")
    print(f"Đổi ngược: trỏ alias '{ALIAS}' về '{cu[0] if cu else '?'}'. Collection cũ được giữ nguyên.")


def main() -> None:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--xem", action="store_true")
    g.add_argument("--ghi", action="store_true")
    g.add_argument("--so-sanh", nargs="+", metavar="CAU_HOI")
    g.add_argument("--doi-alias", action="store_true")
    ap.add_argument("--tran", type=int, default=16, help="trần số lượt gọi mô hình")
    a = ap.parse_args()
    client = QdrantClient(url=settings.qdrant_url)

    if a.xem:
        for pid, p in gop_payload(client, doc_ban_chep()):
            print("=" * 74)
            print(p["title"], "|", p["topic"], "|", len(p["text"]), "ký tự")
            print(p["text"][:260].replace("\n", " ⏎ "))
        print("\nChưa gọi mô hình, chưa ghi gì.")
    elif a.ghi:
        ghi(client, a.tran)
    elif a.so_sanh:
        so_sanh(client, a.so_sanh, a.tran)
    else:
        doi_alias(client)


if __name__ == "__main__":
    main()
