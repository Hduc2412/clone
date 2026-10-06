"""Hai lượt Agent chủ động nói — dựng bằng template, không gọi mô hình.

## Vì sao template chứ không phải mô hình

Hạn mức gói miễn phí là 20 lượt mỗi ngày mỗi model, và nó đã cạn giữa một lượt
đo thật ngày 01/10. Hai lượt chủ động này xuất hiện với **mọi** ứng viên, nên nếu
chúng bắt buộc gọi mô hình thì mười ứng viên là hết hạn mức của cả ngày — và
người thứ mười một gửi CV xong sẽ thấy một màn hình im lặng.

Nên văn bản ở đây dựng xong bằng dữ liệu có cấu trúc. Mô hình chỉ **diễn đạt lại**
ở tầng trên (`orchestrator`), và nếu nó không trả lời được thì bản này đi ra màn
hình nguyên vẹn. Cùng khuôn với `text_source: "mo_hinh" | "ghep_san"` đã chạy ở
phòng tư vấn theo đơn.

## Hai mốc, và vì sao phải là hai

**Sau khi đọc CV** — trước cả bước xác nhận. Đây là lúc ứng viên vừa làm một việc
(gửi tệp) và đang chờ xem máy hiểu được gì. Nói lại thứ đã đọc được là cách duy
nhất để họ phát hiện máy đọc nhầm; và hỏi 1–2 thứ còn thiếu ngay lúc họ còn đang
chú ý thì tỉ lệ được trả lời cao hơn hẳn so với hỏi sau.

**Sau khi đối chiếu** — lúc có kết quả. Danh sách thẻ đơn thì đọc được, nhưng nó
không trả lời câu người ta thật sự hỏi: *"tóm lại tôi có cơ hội không, và vướng ở
đâu"*. Một đoạn ba câu trước danh sách làm đúng việc đó.

## Không hứa, không thêm số

Mọi con số trong hai lượt này đều lấy từ dữ liệu đã có: số trường đọc được, số
đơn đạt, mã đơn hạng nhất. Không có chỗ nào tính thêm, nên không có chỗ nào bịa.

Và không câu nào nói "bạn sẽ đỗ", "bạn chắc chắn đi được". Kết quả đối chiếu là
mức độ phù hợp trên giấy tờ — câu miễn trừ ấy đã nằm trong `to_public_payload`,
nên ở đây chỉ cần không nói ngược lại nó.
"""
from typing import Any

from app.consultation import next_question
from app.db import candidate_documents as tai_lieu_cv
from app.db import candidate_profiles as profiles
from app.matching import explain


# Thứ tự kể lại thứ đọc được từ CV. Không phải thứ tự chữ cái: ba trường đầu là
# ba trường quyết định ai bị loại ở bộ lọc cứng, nên chúng phải được nhìn thấy
# trước — nếu máy đọc nhầm một trong ba, đó là chỗ phải phát hiện ngay.
THU_TU_KE = (
    "japanese_level",
    "education_level",
    "birth_year",
    "major",
    "experience_years",
    "care_experience",
    "full_name",
    "phone",
)

TEN_TIENG_VIET: dict[str, str] = {
    "full_name": "họ tên",
    "birth_year": "năm sinh",
    "gender": "giới tính",
    "education_level": "bằng cấp",
    "major": "chuyên ngành",
    "japanese_level": "trình độ tiếng Nhật",
    "experience_years": "số năm kinh nghiệm",
    "care_experience": "kinh nghiệm chăm sóc",
    "phone": "số điện thoại",
}

# Kể nhiều nhất bốn mục.
#
# Bản đầu kể hết tám trường đọc được, và câu ra trông như một bản trút dữ liệu:
# "trình độ tiếng Nhật N4, bằng cấp Cao đẳng, năm sinh 1999, chuyên ngành Điều
# dưỡng, số năm kinh nghiệm 3 năm, kinh nghiệm chăm sóc đã từng, họ tên ... và
# số điện thoại ...". Không ai soát một câu như thế, mà soát lại chính là việc
# câu này tồn tại để làm.
#
# Bốn mục đầu theo `THU_TU_KE` là bốn mục quyết định ai bị loại ở bộ lọc cứng.
# Phần còn lại vẫn hiện đầy đủ trên biểu mẫu ngay bên dưới, nơi sửa được từng ô.
TOI_DA_KE = 4


# Hồ sơ đến từ đâu — quyết định lượt mở đầu được phép nói gì.
#
# Bản đầu chỉ nhìn **nguồn của từng trường** trên hồ sơ hiện tại, và suy ra "không
# có trường nguồn `cv` nghĩa là đọc CV hỏng". Sai ở hai chỗ, cùng bắt trên trình
# duyệt ngày 06/10: khách khai bằng biểu mẫu, không gửi tệp nào, vẫn nghe "Mình đã
# nhận được tệp của bạn nhưng chưa rút được thông tin nào"; và khách đã đọc CV ra
# chín trường rồi bấm "Sửa hồ sơ" — biểu mẫu ghi lại mọi trường thành
# `user_confirmed` — cũng nghe đúng câu ấy. Căn cứ đúng là **tệp CV**, không phải
# nguồn của trường.
KHAI_TAY = "khai_tay"        # phiên không có tệp CV nào
CV_HONG = "cv_hong"          # có tệp, nhưng máy không rút được trường nào
CV_DOC_DUOC = "cv_doc_duoc"  # có tệp, máy rút được ít nhất một trường


def nguon_ho_so(tai_lieu: dict[str, Any] | None) -> str:
    """Phân loại theo tệp CV mới nhất của phiên (`candidate_documents`)."""
    if not tai_lieu:
        return KHAI_TAY
    if tai_lieu.get("status") == tai_lieu_cv.STATUS_EXTRACTED and tai_lieu.get("extracted_fields"):
        return CV_DOC_DUOC
    return CV_HONG


def sau_khi_doc_cv(profile: dict[str, Any] | None, *, nguon: str = CV_DOC_DUOC) -> str:
    """Lượt mở đầu ngay sau khi có hồ sơ — từ CV hoặc từ biểu mẫu.

    Ba phần: đã có gì, chỗ nào chưa rõ, và một hoặc hai câu hỏi. Câu "đây là thứ
    máy đọc được" chỉ đi kèm khi thật sự có thứ máy đọc được.
    """
    if not profile:
        if nguon == CV_HONG:
            return (
                "Mình đã nhận được tệp của bạn nhưng chưa đọc được thông tin nào từ "
                "đó. Bạn khai nhanh vài mục bằng biểu mẫu bên dưới nhé."
            )
        return (
            "Mình chưa nhận được hồ sơ nào. Bạn gửi CV lên, hoặc khai nhanh vài "
            "mục bằng biểu mẫu bên dưới nhé."
        )

    profiles.decorate(profile)
    cau: list[str] = []

    if nguon == CV_DOC_DUOC:
        doc_duoc = _ke_lai(profile, chi_nguon=("cv",))
        if doc_duoc:
            cau.append(f"Mình đã đọc CV của bạn. Hồ sơ hiện ghi nhận {doc_duoc}.")
            # Nói rõ đây là thứ MÁY đọc, chưa phải thứ người đã xác nhận. Một câu,
            # đặt ngay sau phần kể lại — để ai đọc nhanh cũng không bỏ qua.
            cau.append(
                "Đây là thứ máy đọc được, bạn xem lại giúp mình xem có chỗ nào lệch không."
            )
        else:
            # Đọc được, nhưng khách đã tự xác nhận lại mọi trường từ đó. Không còn
            # gì là "máy đọc" để nhờ soát, và kể lại như máy đọc là nhận công sai chỗ.
            da_khai = _ke_lai(profile)
            cau.append(
                "Mình đã đọc CV của bạn, và bạn đã xác nhận lại thông tin"
                + (f": {da_khai}." if da_khai else ".")
            )
    else:
        da_khai = _ke_lai(profile, chi_nguon=("user_confirmed", "staff"))
        if nguon == CV_HONG:
            cau.append(
                "Mình đã nhận được tệp của bạn nhưng chưa rút được thông tin nào "
                "chắc chắn từ đó."
            )
            if da_khai:
                cau.append(f"Theo thông tin bạn khai, hồ sơ hiện ghi nhận {da_khai}.")
        else:
            cau.append(
                f"Mình đã nhận thông tin bạn khai. Hồ sơ hiện ghi nhận {da_khai}."
                if da_khai
                else "Mình đã nhận thông tin bạn khai."
            )

    hoi = next_question.chon(profile)
    if hoi:
        cau.append(" ".join(hoi))

    return " ".join(cau)


def sau_matching(
    log: dict[str, Any] | None,
    *,
    profile: dict[str, Any] | None = None,
) -> str:
    """Lượt mở đầu ngay sau khi có kết quả đối chiếu."""
    if log is None:
        return (
            "Hồ sơ của bạn đã được ghi nhận. Bạn bấm đối chiếu để xem mình hợp "
            "những đơn nào nhé."
        )

    dat = [row for row in log.get("items") or () if row.get("eligible")]
    da_xet = log.get("total_considered") or len(log.get("items") or ())
    cau: list[str] = []

    if not dat:
        cau.append(
            f"Mình đã đối chiếu hồ sơ của bạn với {da_xet} đơn đang tuyển và "
            f"hiện chưa có đơn nào bạn đủ điều kiện nộp."
        )
        # Không dừng ở đó. Người vừa đọc câu trên cần biết vì sao và còn đường nào.
        ly_do = _ly_do_pho_bien(log)
        if ly_do:
            cau.append(f"Chỗ vướng nhiều nhất là {ly_do}.")
    else:
        cau.append(
            f"Hồ sơ của bạn hiện phù hợp với {len(dat)} đơn trên {da_xet} đơn "
            f"đang tuyển."
        )
        hang_nhat = _hang_nhat(dat)
        if hang_nhat:
            ma = hang_nhat.get("code") or ""
            ten = hang_nhat.get("title") or ""
            diem_manh = _diem_manh(hang_nhat)
            if diem_manh:
                cau.append(f"Đơn {ma} – {ten} phù hợp nhất, nhờ {diem_manh}.")
            else:
                # Không có dòng mềm nào được cộng điểm, tức **chưa xếp hạng
                # được**. Bản trước nói "đang xếp hạng cao nhất" ở đây, và đó là
                # một thứ hạng tuỳ ý: mọi đơn đều 0 điểm mềm nên thứ tự chỉ do
                # hạn nộp và mã đơn quyết. Nói "cao nhất" là biến một thứ tự
                # ngẫu nhiên thành một lời khuyên.
                cau.append(
                    "Mình chưa so được thứ tự giữa các đơn vì bạn chưa nêu "
                    "nguyện vọng — khu vực, loại cơ sở, lương hay chi phí."
                )

    # Dữ liệu còn thiếu phải nói ở CẢ HAI nhánh.
    #
    # Nhánh có đơn đạt thì dễ bị bỏ qua nhất: kết quả nhìn đẹp, nên không ai nghĩ
    # tới việc nó được xếp hạng trên dữ liệu khuyết. Mà chính lúc ấy mới cần nói —
    # một trường thiếu có thể đổi cả thứ tự, và người đọc đang sắp chọn đơn.
    thieu = next_question.chon(profile) if profile else []
    if thieu:
        cau.append(
            "Kết quả này còn cần bổ sung thông tin mới chắc. " + " ".join(thieu)
        )

    return " ".join(cau)


def _ke_lai(
    profile: dict[str, Any], *, chi_nguon: tuple[str, ...] | None = None
) -> str:
    """Danh sách giá trị đã có, viết thành một câu đọc được.

    `chi_nguon` giới hạn theo nguồn — lượt sau khi đọc CV chỉ kể thứ **máy đọc
    được**, không kể lẫn thứ khách tự khai từ trước. Trộn hai nguồn vào một câu
    "mình đã đọc CV của bạn" là nhận công cho máy ở chỗ không phải của nó, và
    khách sẽ không đi soát lại những dòng ấy.
    """
    labels = profile.get("labels") or {}
    manh: list[str] = []

    for key in THU_TU_KE:
        if len(manh) >= TOI_DA_KE:
            break
        for muc in ("fields", "preferences"):
            cell = (profile.get(muc) or {}).get(key)
            if not isinstance(cell, dict):
                continue
            gia_tri = cell.get("value")
            if gia_tri in (None, ""):
                continue
            if chi_nguon and cell.get("source") not in chi_nguon:
                continue
            manh.append(_cum(key, gia_tri, labels))
            break

    if not manh:
        return ""
    if len(manh) == 1:
        return manh[0]
    return ", ".join(manh[:-1]) + " và " + manh[-1]


def _cum(key: str, gia_tri: Any, labels: dict[str, Any]) -> str:
    """Một cụm từ đọc được, không phải cặp "tên trường + giá trị".

    Ghép thẳng tên trường với giá trị cho ra những cụm không ai nói ra miệng:
    *"kinh nghiệm chăm sóc đã từng"*, *"số năm kinh nghiệm 3 năm"*. Câu mở đầu
    là chỗ ứng viên quyết định có tin hệ thống đọc đúng hay không, nên nó phải
    đọc như tiếng Việt.
    """
    if key == "care_experience":
        return "đã từng chăm sóc người bệnh" if gia_tri else "chưa từng chăm sóc người bệnh"
    if key == "experience_years":
        # 3.0 đọc ra "3 năm". Một số thập phân treo ở đó làm câu nói trông như
        # máy đang đọc bảng tính.
        so = int(gia_tri) if float(gia_tri).is_integer() else gia_tri
        return f"{so} năm kinh nghiệm"
    if key == "japanese_level":
        nhan = labels.get(key) or gia_tri
        return f"tiếng Nhật {nhan}"
    if key == "education_level":
        return f"bằng {str(labels.get(key) or gia_tri).lower()}"
    if key == "birth_year":
        return f"sinh năm {gia_tri}"
    if key == "major":
        return f"chuyên ngành {gia_tri}"
    if key == "gender":
        return str(labels.get(key) or gia_tri).lower()
    if key == "phone":
        return f"số điện thoại {gia_tri}"
    return f"{TEN_TIENG_VIET.get(key, key)} {labels.get(key) or gia_tri}"


def _viet_thuong_dau(cau: str) -> str:
    """Hạ chữ đầu, giữ nguyên phần còn lại.

    `str.lower()` làm hỏng nhãn có danh từ riêng: nhãn tiêu chí "Tiếng Nhật" đi
    vào giữa câu thành "tiếng nhật". Ở đây chỉ cần chữ đầu thành chữ thường để
    nhãn ghép được vào giữa câu, còn "Nhật" phải giữ nguyên.
    """
    return cau[:1].lower() + cau[1:] if cau else cau


def _hang_nhat(dat: list[dict[str, Any]]) -> dict[str, Any] | None:
    for row in dat:
        if row.get("rank") == 1:
            return row
    return dat[0] if dat else None


def _diem_manh(item: dict[str, Any]) -> str:
    """Hai lý do mềm được cộng điểm cao nhất, viết lại thành cụm ngắn.

    Lấy từ `soft_rows` đã chấm, không tự nghĩ — nên câu "nhờ ..." luôn trỏ về
    đúng dòng có trong bảng điểm mà khách bấm vào xem được.

    ## Điểm dương một mình chưa đủ để thành lý do

    `weights.json` cho dòng chi phí **5 điểm khi chưa rõ** — có chủ ý, để một đơn
    không công bố chi phí khỏi bị đẩy xuống dưới một đơn đã biết là quá khả năng
    (`test_unknown_cost_scores_five`). Hệ quả: khách chưa nêu ngân sách thì mọi
    đơn đều có đúng 5 điểm chi phí.

    Lọc theo điểm dương thôi thì câu mở đầu thành *"phù hợp nhất, nhờ chi phí"*
    trong khi chính dòng ấy ghi "chưa rõ khả năng" — khen một thứ chưa ai biết.
    Bắt được ngày 05/10 qua `scripts/nghiem_thu_xuyen_suot.py`, ca
    `THIEU-THONG-TIN`.

    Nên dùng lại đúng điều kiện của `explain.render_template_text`: điểm dương
    **và** kết cục không phải `unknown`. Hai chỗ trả lời cùng một câu hỏi — "dòng
    này có đáng nêu thành lý do không" — thì phải dùng cùng một luật.
    """
    dong = [
        d
        for d in item.get("soft_rows") or ()
        if isinstance(d, dict)
        and (d.get("points") or 0) > 0
        and d.get("outcome") not in explain.NON_REASONS
    ]
    dong.sort(key=lambda d: -(d.get("points") or 0))
    # Hạ chữ đầu của TỪNG nhãn, không phải của cụm đã ghép.
    #
    # Ghép trước rồi hạ một lần thì nhãn thứ hai giữ nguyên chữ hoa, và câu ra
    # "nhờ khu vực và Loại hình cơ sở" — bắt được trên trình duyệt thật 01/10.
    cum = [_viet_thuong_dau(str(d.get("label") or "").strip()) for d in dong[:2]]
    cum = [c for c in cum if c]
    if not cum:
        return ""
    return " và ".join(cum)


def _ly_do_pho_bien(log: dict[str, Any]) -> str:
    """Tiêu chí làm trượt nhiều đơn nhất, để nói đúng chỗ vướng thật.

    Đếm trên các dòng điều kiện cứng **không đạt** của mọi đơn đã xét. Người bị
    báo "không có đơn nào" cần biết vướng ở tiếng Nhật hay vướng ở tuổi — hai thứ
    dẫn tới hai việc hoàn toàn khác nhau, một cái học được, một cái không.

    Chỉ đếm `KHONG_DAT`, bỏ `CHUA_RO`. Thiếu dữ liệu không phải là không đạt, và
    bộ đối chiếu cũng không loại đơn vì nó — gộp hai thứ vào đây là nói với người
    ta rằng họ trượt vì một điều kiện mà thực ra chưa ai biết họ có đạt hay không.

    Đơn bị loại trong nhật ký đã được rút gọn còn **đúng những dòng không đạt**
    (`matching_service._gon_lai`), nên phép đếm này rẻ và không cần lọc gì thêm
    ngoài việc bỏ `CHUA_RO`.
    """
    from app.matching.engine import KHONG_DAT

    dem: dict[str, int] = {}
    for row in log.get("items") or ():
        for dong in row.get("hard_rows") or ():
            if not isinstance(dong, dict) or dong.get("result") != KHONG_DAT:
                continue
            ten = str(dong.get("label") or "").strip()
            if ten:
                dem[ten] = dem.get(ten, 0) + 1
    if not dem:
        return ""
    # Hòa phiếu thì lấy tên ngắn hơn, rồi tới thứ tự chữ cái — phải tất định,
    # vì cùng một kết quả đối chiếu không được sinh ra hai câu khác nhau.
    return _viet_thuong_dau(min(dem.items(), key=lambda c: (-c[1], len(c[0]), c[0]))[0])
