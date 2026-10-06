"""Hợp đồng dữ liệu giữa mô hình và backend — và chốt chặn trên mọi đề xuất.

## Mô hình đề xuất, backend quyết

Mô hình được trả về một khối có cấu trúc, trong đó có `facts_to_save`: những điều
nó nghe được trong hội thoại và cho là nên lưu vào hồ sơ. Đây là thứ **nguy hiểm
nhất** trong cả tính năng, vì hồ sơ là đầu vào của bộ đối chiếu — một giá trị sai
lọt vào đó không chỉ sai một câu trả lời, nó đổi danh sách đơn mà một người thật
nhìn thấy.

Nên bốn thứ bị ép ở đây, không phải ở prompt:

1. **Trường phải nằm trong danh sách cho phép.** Lấy thẳng từ
   `candidate_profiles.FIELD_KEYS` và `PREFERENCE_KEYS` — một nguồn duy nhất, nên
   thêm trường mới vào hồ sơ là Agent ghi được ngay, còn mô hình bịa ra tên
   trường thì bị loại.

2. **Kiểu dữ liệu phải đúng.** Dùng chính bộ chuẩn hóa của đường API hồ sơ, không
   viết bộ thứ hai: hai bộ thì sớm muộn lệch nhau, và lúc lệch thì đường nào lỏng
   hơn trở thành đường thật.

3. **Nguồn luôn là `chat`.** Mô hình nói `source` gì cũng bị ghi đè. Nếu nhận
   nguồn từ mô hình thì nó khai `user_confirmed` một lần là dữ liệu máy nghe được
   bỗng mang dấu "người đã xác nhận" — và theo thứ tự ưu tiên nguồn, nó sẽ **đè
   lên dữ liệu đọc từ CV**. Prompt injection chỉ cần đúng một câu để làm việc đó.

4. **`requires_confirmation` luôn đúng.** Không có đường nào để một đề xuất tự
   vào hồ sơ. Giá trị hiện lên giao diện dạng "bạn vừa nói ... đúng không?" và
   chỉ được lưu khi người dùng bấm.

## Vì sao không để mô hình khai `current_stage`

Bản thiết kế ban đầu có trường ấy trong khối JSON. Nó bị bỏ: giai đoạn suy ra từ
dữ liệu (`state.py`), và hỏi mô hình một thứ đã biết chắc chỉ mở đường cho nó trả
lời khác. Mô hình **đọc** được giai đoạn, không **ghi** được.

Cùng lý do với `interested_order_codes`: đơn khách đang xem đã nằm trong bộ nhớ
phiên, do một hành vi thật (mở màn hình đơn đó) ghi vào. Để mô hình khai lại là
cho phép nó đổi đơn khách đang xem bằng một câu văn.
"""
import json
import logging
from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError

from app.agent import state
from app.db import candidate_profiles as profiles


logger = logging.getLogger(__name__)

# Nguồn của mọi thứ nghe được trong hội thoại. Hằng số, không phải mặc định —
# không có đường nào truyền giá trị khác vào.
NGUON_HOI_THOAI = "chat"

# Trường Agent được phép đề xuất. Một nguồn duy nhất với hồ sơ thật.
TRUONG_CHO_PHEP: frozenset[str] = profiles.FIELD_KEYS | profiles.PREFERENCE_KEYS

# Trần số đề xuất mỗi lượt. Mô hình trả về mười đề xuất trong một lượt thì đó
# không phải là nó nghe được mười điều — đó là nó đang đoán.
TOI_DA_DE_XUAT = 3

# Hành động mô hình được đề nghị. Nó KHÔNG được đề nghị `register`: đăng ký là
# hành vi tạo hồ sơ cho nhân viên gọi điện, và nó phải đến từ một cú bấm của
# người dùng trên màn hình có đủ thông tin, không từ một câu văn.
HANH_DONG_CHO_PHEP: frozenset[str] = frozenset(
    {state.HD_HOI, state.HD_XAC_NHAN, state.HD_XEM_DON, state.HD_NHAN_VIEN, state.HD_KHONG}
)


def _bang_nhan() -> dict[str, dict[str, str]]:
    """Trường nào là mã danh mục, tra nhãn ở bảng nào — cùng bảng `profiles.decorate` dùng."""
    from app.matching import catalog

    return {
        "japanese_level": catalog.JAPANESE_LEVEL_LABELS,
        "education_level": catalog.EDUCATION_LABELS,
        "gender": catalog.GENDER_LABELS,
        "desired_employer_type": catalog.EMPLOYER_TYPE_LABELS,
        "desired_region_group": catalog.REGION_LABELS,
    }


def nhan_gia_tri(field_name: str, value: Any) -> str | None:
    """Nhãn tiếng Việt của một giá trị mã danh mục, hoặc `None` nếu không phải mã.

    Khách phải đọc rồi bấm "Đúng, lưu lại". Kiểm trên trình duyệt ngày 06/10, câu
    xác nhận hiện "Loại hình: **vien_duong_lao**" — mã máy, không phải chữ.
    """
    bang = _bang_nhan().get(field_name)
    if bang is None or not isinstance(value, str):
        return None
    return bang.get(value)


@dataclass(frozen=True)
class DeXuatGhi:
    """Một điều Agent nghe được và đề nghị lưu. Chưa phải dữ liệu trong hồ sơ."""

    field: str
    value: Any
    muc: str  # "fields" | "preferences" — để đường ghi biết đặt vào đâu
    evidence: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "value": self.value,
            "value_label": nhan_gia_tri(self.field, self.value),
            # Hiện ra ngoài để giao diện và người đọc API thấy rõ: đây là thứ
            # nghe trong hội thoại, và nó cần người xác nhận.
            "source": NGUON_HOI_THOAI,
            "requires_confirmation": True,
            "evidence": self.evidence,
        }


@dataclass(frozen=True)
class KetQua:
    """Những gì backend chấp nhận từ một lượt của mô hình."""

    reply: str
    intent: str = ""
    de_xuat: tuple[DeXuatGhi, ...] = ()
    hanh_dong_goi_y: state.HanhDong | None = None
    can_nhan_vien: bool = False
    ly_do_nhan_vien: str = ""
    # Những gì bị loại và vì sao. Không phải để gỡ lỗi — đây là số liệu chứng
    # minh chốt chặn đang làm việc, và là thứ hội đồng sẽ hỏi.
    da_loai: tuple[str, ...] = field(default=())

    def as_dict(self) -> dict[str, Any]:
        return {
            "reply": self.reply,
            "intent": self.intent,
            "facts_to_save": [d.as_dict() for d in self.de_xuat],
            "suggested_action": (
                self.hanh_dong_goi_y.as_dict() if self.hanh_dong_goi_y else None
            ),
            "handoff": {
                "required": self.can_nhan_vien,
                "reason": self.ly_do_nhan_vien,
            },
            "rejected": list(self.da_loai),
        }


def doc_khoi_json(van_ban: str) -> dict[str, Any] | None:
    """Bóc khối JSON ra khỏi câu trả lời của mô hình.

    Mô hình hay bọc JSON trong ```json ... ``` dù prompt đã nói đừng. Không coi
    đó là lỗi của nó: cắt dấu bọc ở đây rẻ hơn nhiều so với việc mất cả lượt.

    Trả `None` khi không bóc được — nơi gọi phải có đường đi tiếp bằng văn bản
    thuần, vì một lượt hỏng định dạng không được làm ứng viên đứng giữa chừng.
    """
    sach = (van_ban or "").strip()
    if sach.startswith("```"):
        sach = sach.split("\n", 1)[-1] if "\n" in sach else ""
        if sach.rstrip().endswith("```"):
            sach = sach.rstrip()[:-3]
    sach = sach.strip()
    if not sach.startswith("{"):
        # Có khi mô hình nói một câu dẫn rồi mới tới JSON. Lấy từ dấu ngoặc đầu
        # tới dấu ngoặc cuối.
        dau, cuoi = sach.find("{"), sach.rfind("}")
        if dau < 0 or cuoi <= dau:
            return None
        sach = sach[dau : cuoi + 1]
    try:
        khoi = json.loads(sach)
    except json.JSONDecodeError:
        return None
    return khoi if isinstance(khoi, dict) else None


def kiem_de_xuat(
    tho: Any,
    *,
    profile: dict[str, Any] | None,
    nguon_se_ghi: str = NGUON_HOI_THOAI,
) -> tuple[list[DeXuatGhi], list[str]]:
    """Lọc `facts_to_save` của mô hình. Trả `(đã nhận, đã loại kèm lý do)`.

    Không ném lỗi: một đề xuất sai không được làm mất cả câu trả lời. Thứ bị loại
    thì ghi lại lý do để đọc được từ ngoài.

    ## `nguon_se_ghi` — và vì sao nó phải là tham số

    Hàm này dùng cho **hai đường**, và phép kiểm "đã có nguồn đáng tin hơn" cho
    hai kết quả khác nhau ở hai đường đó:

    - Đường **đề xuất**: giá trị rồi sẽ được ghi với nguồn `chat`. Một trường đã
      có giá trị từ CV thì không nên đem ra đề xuất lại.
    - Đường **xác nhận**: người dùng vừa đọc giá trị trên màn hình và bấm đồng ý,
      nên nó được ghi với nguồn `user_confirmed` — và nguồn ấy **đè lên `cv`**.
      Đó là đúng: người vừa nói máy đọc sai thì họ đáng tin hơn máy đọc.

    Bản đầu không có tham số này nên luôn so với `chat`, và đường xác nhận từ
    chối mọi lần ứng viên sửa một trường máy đã đọc được — đúng việc nó tồn tại
    để làm. Bắt được bằng ca kiểm thử `test_4_gia_tri_nguoi_xac_nhan_de_len...`.

    Nguồn `staff` vẫn chặn được cả hai đường, vì nó xếp trên `user_confirmed`:
    nhân viên đã chốt một giá trị thì ứng viên không lặng lẽ đổi qua đường này.
    """
    nhan: list[DeXuatGhi] = []
    loai: list[str] = []

    if not isinstance(tho, list):
        if tho not in (None, ""):
            loai.append("facts_to_save không phải danh sách")
        return nhan, loai

    da_nhan: set[str] = set()
    for muc_tho in tho[:TOI_DA_DE_XUAT]:
        if not isinstance(muc_tho, dict):
            loai.append("một đề xuất không phải đối tượng")
            continue

        ten = str(muc_tho.get("field") or "").strip()
        if ten not in TRUONG_CHO_PHEP:
            loai.append(f"trường không cho phép ghi: {ten!r}")
            continue

        # Cùng một trường hai lần trong một lượt: giữ cái đầu, bỏ cái sau.
        #
        # Không phải lo chuyện gọn gàng. Giao diện hiện mỗi đề xuất thành một
        # câu "bạn vừa nói ... đúng không?", nên hai đề xuất cùng trường với hai
        # giá trị khác nhau là hai câu hỏi mâu thuẫn hiện cạnh nhau — và bấm cái
        # nào trước cũng được, kết quả tùy thứ tự người dùng bấm.
        if ten in da_nhan:
            loai.append(f"{ten}: đã có đề xuất khác cho cùng trường trong lượt này")
            continue

        gia_tri = muc_tho.get("value")
        if gia_tri in (None, ""):
            loai.append(f"{ten}: không có giá trị")
            continue

        sach, loi = _chuan_hoa(ten, gia_tri)
        if loi:
            loai.append(f"{ten}: {loi}")
            continue

        # Đã có giá trị từ nguồn đáng tin hơn thì không đề xuất nữa. Luật ưu tiên
        # nguồn ở tầng ghi cũng sẽ chặn, nhưng hỏi lại một thứ nhân viên vừa chốt
        # là làm người dùng tưởng hệ thống quên.
        if _da_co_nguon_manh_hon(profile, ten, nguon_se_ghi):
            loai.append(f"{ten}: đã có giá trị từ nguồn đáng tin hơn")
            continue

        nhan.append(
            DeXuatGhi(
                field=ten,
                value=sach,
                muc="fields" if ten in profiles.FIELD_KEYS else "preferences",
                evidence=str(muc_tho.get("evidence") or "")[:300],
            )
        )
        da_nhan.add(ten)

    if len(tho) > TOI_DA_DE_XUAT:
        loai.append(
            f"bỏ {len(tho) - TOI_DA_DE_XUAT} đề xuất vượt trần {TOI_DA_DE_XUAT} mỗi lượt"
        )

    return nhan, loai


def _chuan_hoa(ten: str, gia_tri: Any) -> tuple[Any, str]:
    """Chuẩn hóa bằng **chính bộ của đường API hồ sơ**, không viết bộ thứ hai.

    Hai bộ chuẩn hóa thì sớm muộn lệch nhau, và lúc lệch thì đường nào lỏng hơn
    trở thành đường thật — ở đây đường lỏng hơn sẽ là đường mô hình đi.
    """
    from app.api import profiles as api_profiles

    mo_hinh = (
        api_profiles.FieldsPayload
        if ten in profiles.FIELD_KEYS
        else api_profiles.PreferencesPayload
    )
    try:
        da_kiem = mo_hinh.model_validate({ten: gia_tri})
    except Exception as exc:  # noqa: BLE001 — pydantic ném nhiều loại
        return None, _gon_loi(exc)

    ra = getattr(da_kiem, ten, None)
    if ra is None:
        return None, "giá trị không hợp lệ"
    return ra, ""


def _gon_loi(exc: Exception) -> str:
    """Một dòng ngắn đọc được, không phải cả vết ngoại lệ của pydantic.

    Pydantic in ra ba dòng cho mỗi lỗi: tên trường, câu mô tả, rồi khối
    `[type=..., input_value=...]`. Bản đầu của hàm này lấy dòng đầu tiên không
    nằm trong danh sách bỏ qua, nên nó trả về đúng **tên trường** — và thông báo
    thành `"birth_year: birth_year"`, không nói gì cả.

    Dòng cần lấy là dòng mô tả, tức dòng thứ hai của mỗi lỗi. Nhận ra nó bằng
    việc nó thụt lề, còn tên trường thì không.
    """
    if isinstance(exc, ValidationError):
        for loi in exc.errors():
            cau = str(loi.get("msg") or "").strip()
            if cau:
                # Pydantic thêm tiền tố "Value error, " cho lỗi do validator của
                # mình ném — bỏ đi, vì câu phía sau đã là câu người đọc được.
                return cau.removeprefix("Value error, ")[:120]
        return "giá trị không hợp lệ"

    for d in str(exc).splitlines():
        if not d.startswith((" ", "\t")):
            continue
        sach = d.strip()
        if sach and not sach.startswith("[type="):
            return sach.removeprefix("Value error, ")[:120]
    return "giá trị không hợp lệ"


def _da_co_nguon_manh_hon(
    profile: dict[str, Any] | None, ten: str, nguon_se_ghi: str
) -> bool:
    """Giá trị đang có đến từ nguồn xếp trên nguồn sắp ghi hay không."""
    from app.matching.catalog import SOURCE_PRIORITY

    if not profile:
        return False
    for muc in ("fields", "preferences"):
        cell = (profile.get(muc) or {}).get(ten)
        if isinstance(cell, dict) and cell.get("value") not in (None, ""):
            hien_tai = SOURCE_PRIORITY.get(str(cell.get("source") or ""), 0)
            return hien_tai > SOURCE_PRIORITY.get(nguon_se_ghi, 0)
    return False


def kiem_hanh_dong(tho: Any) -> tuple[state.HanhDong | None, list[str]]:
    """Hành động mô hình gợi ý. Loại thẳng nếu không nằm trong danh sách."""
    if not isinstance(tho, dict):
        return None, ([] if tho in (None, "") else ["next_best_action không phải đối tượng"])

    loai_hd = str(tho.get("type") or "").strip()
    if loai_hd not in HANH_DONG_CHO_PHEP:
        return None, [f"hành động không cho phép: {loai_hd!r}"]

    nhan = str(tho.get("label") or "").strip()[:80]
    muc_tieu = tho.get("target")
    muc_tieu = str(muc_tieu).strip()[:20] if muc_tieu else None
    return state.HanhDong(loai_hd, nhan or "Bước tiếp theo", muc_tieu), []
