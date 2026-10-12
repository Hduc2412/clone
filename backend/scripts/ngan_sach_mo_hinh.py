# -*- coding: utf-8 -*-
"""Ngân sách cứng cho các lượt gọi mô hình thật trong một đợt nghiệm thu (yêu cầu 08/10).

Luật của đợt:

- Tối đa N lượt gọi tới dịch vụ mô hình, **tính mọi lượt**: đọc CV, model dự phòng,
  thử lại — bất kỳ yêu cầu HTTP nào tới `generativelanguage.googleapis.com`.
- Gặp **429** thì dừng mọi lượt gọi thật còn lại.
- Gặp **hai lỗi dịch vụ liên tiếp** (5xx, hết giờ chờ, lỗi kết nối) thì dừng.
- Không chờ, không thử lại.

Chặn ở tầng HTTP chứ không ở tầng client tư vấn, vì hai lẽ. Client gộp 429, 503 và
hết giờ chờ vào cùng một lý do `khong_goi_duoc` — đứng ở trên nó thì không phân biệt
được 429 để dừng. Và chặn ở `httpx.AsyncClient.post` thì đếm được cả những đường gọi
không đi qua client tư vấn (đọc CV, diễn đạt kết quả đối chiếu).

Lượt bị chặn không bao giờ rời máy: nó ném `httpx.ConnectError` ngay tại chỗ, và
client xử lý như một lần không gọi được — tức ca đó ra `khong_goi_duoc`, được ghi
CHƯA ĐO ĐƯỢC, không bao giờ thành "đạt".
"""
from __future__ import annotations

from dataclasses import dataclass, field

import httpx

MAY_CHU = "generativelanguage.googleapis.com"


@dataclass
class NganSach:
    toi_da: int
    da_goi: int = 0
    loi_lien_tiep: int = 0
    ly_do_dung: str = ""
    nhat_ky: list[dict] = field(default_factory=list)

    @property
    def da_dung(self) -> bool:
        return bool(self.ly_do_dung)

    def _kiem_truoc(self, url: str) -> None:
        if self.da_dung:
            raise httpx.ConnectError(f"ngân sách: đã dừng ({self.ly_do_dung})")
        if self.da_goi >= self.toi_da:
            self.ly_do_dung = f"hết ngân sách {self.toi_da} lượt"
            raise httpx.ConnectError(f"ngân sách: {self.ly_do_dung}")
        self.da_goi += 1

    def _ghi(self, url: str, ket: str) -> None:
        model = url.split("/models/")[-1].split(":")[0] if "/models/" in url else url
        self.nhat_ky.append({"luot": self.da_goi, "model": model, "ket_qua": ket})

    def _loi_dich_vu(self) -> None:
        self.loi_lien_tiep += 1
        if self.loi_lien_tiep >= 2:
            self.ly_do_dung = "hai lỗi dịch vụ liên tiếp"

    def gan(self) -> "NganSach":
        """Gắn vào `httpx.AsyncClient.post` của cả tiến trình. Gọi một lần."""
        goc = httpx.AsyncClient.post
        ngan_sach = self

        async def post(client, url, *args, **kwargs):
            chuoi = str(url)
            if MAY_CHU not in chuoi:
                return await goc(client, url, *args, **kwargs)
            ngan_sach._kiem_truoc(chuoi)
            try:
                tra = await goc(client, url, *args, **kwargs)
            except httpx.HTTPError as exc:
                ngan_sach._ghi(chuoi, type(exc).__name__)
                ngan_sach._loi_dich_vu()
                raise
            ngan_sach._ghi(chuoi, str(tra.status_code))
            if tra.status_code == 429:
                ngan_sach.ly_do_dung = "gặp 429"
            elif tra.status_code >= 500:
                ngan_sach._loi_dich_vu()
            else:
                ngan_sach.loi_lien_tiep = 0
            return tra

        httpx.AsyncClient.post = post
        self._goc = goc
        return self

    def go(self) -> None:
        """Trả `httpx.AsyncClient.post` về như cũ (12/10).

        Thiếu bước này thì bản vá sống tiếp trong tiến trình: ca kiểm thử chạy
        `nghiem_thu_agent.main()` để lại bản vá, các ca sau gắn chồng thêm một lớp và
        đếm một lượt thành hai. Gọi trong `finally`.
        """
        goc = getattr(self, "_goc", None)
        if goc is not None:
            httpx.AsyncClient.post = goc
            self._goc = None
