"""Nghiệm thu chatbot: có trả lời sai khi không đủ căn cứ không.

Trả lời câu hỏi thứ nhất trong `docs/design/13 §4`. Chạy bộ câu hỏi chuẩn ở
`tests/fixtures/chatbot/bo_cau_hoi.json` qua đúng luồng chat thật, rồi chấm từng
câu theo hai tiêu chí ngược nhau.

Chạy:  venv\\Scripts\\python.exe -m scripts.nghiem_thu_chatbot

## Hai loại câu, hai kiểu sai

Câu **phải trả lời** hỏng khi bot từ chối một thứ kho tri thức có sẵn — khách bị
đẩy sang hotline một cách vô ích.

Câu **phải từ chối** hỏng khi bot trả lời một thứ kho không có — đây là kiểu sai
nguy hiểm, vì khách tin và hành động theo. Một câu bịa về chuyện hoàn tiền có thể
khiến người ta nộp hồ sơ với kỳ vọng sai.

Bộ này cố tình có cả hai chiều. Chỉ đo một chiều thì cách "tối ưu" rẻ nhất là cho
bot từ chối mọi thứ, và nó sẽ đạt điểm tuyệt đối trong khi vô dụng.

## Vì sao là script chứ không phải ca kiểm thử

Cần mạng, gọi mô hình thật, và mỗi câu tốn một lượt gọi. Bộ kiểm thử thường phải
chạy được cả khi mất mạng. Đây là việc chạy tay trước mỗi mốc bàn giao.
"""
import asyncio
import json
import re
import sys
import uuid
from pathlib import Path

import app  # noqa: F401  — đặt stdout về UTF-8 để in được tiếng Việt
from app.conversation.fallback_messages import RATE_LIMITED, looks_like_refusal
from app.conversation.response_validator import CORRECT_PHONE, _phones_in
from app.core.config import settings
from app.db.database import close_db, init_db
from app.services.chat_service import process_message


FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "tests"
    / "fixtures"
    / "chatbot"
    / "bo_cau_hoi.json"
)

def la_tu_choi(answer: str, is_fallback: bool) -> bool:
    """Dùng đúng bộ nhận diện của hệ thống, không định nghĩa lại ở đây.

    Trước đây file này giữ một bản sao của mẫu nhận diện. Hai bản sao thì sớm
    muộn cũng lệch nhau, và lúc đó bộ nghiệm thu sẽ báo đạt cho đúng thứ mà hệ
    thống đang đếm sai.
    """
    return bool(is_fallback or looks_like_refusal(answer))


# Nghỉ giữa các câu để không dồn cục lên dịch vụ. Lưu ý hạn mức gói miễn phí là
# hai mươi lượt **mỗi ngày** cho mỗi model, không phải mỗi phút — nghỉ lâu hơn
# cũng không giúp gì, đó là lý do bộ này phải chạy được thành nhiều đợt.
NGHI_GIUA_CAU = 4.0


def _chuan_hoa(text: str) -> str:
    """Đưa hai bên về cùng một dạng trước khi so khớp.

    Bỏ dấu chấm ngăn nghìn, rồi quy "N triệu" về số nguyên. Thiếu bước sau thì
    "90 triệu" và "90.000.000" thành hai chuỗi khác nhau, và bộ nghiệm thu sẽ
    chấm hỏng một câu trả lời hoàn toàn đúng — chỉ vì cách viết số.
    """
    text = re.sub(r"\s+", " ", text.replace(".", "")).casefold()
    text = re.sub(r"(\d+)\s*triệu", lambda m: str(int(m.group(1)) * 1_000_000), text)
    return text


def kiem_tra_kho_tri_thuc() -> str | None:
    """Kho tri thức phải với tới được trước khi đo.

    Không có bước này thì Qdrant tắt sẽ khiến **mọi** câu rơi vào câu dự phòng:
    phần phải-trả-lời hỏng sạch, phần phải-từ-chối đạt sạch. Nhìn bảng kết quả
    thì tưởng chatbot hỏng, trong khi thật ra chưa đo được gì cả — kiểu sai tệ
    nhất của một bộ nghiệm thu là báo sai về chính nó.
    """
    from qdrant_client.http.exceptions import ResponseHandlingException, UnexpectedResponse

    from app.db.qdrant import COLLECTION_NAME, get_qdrant_client

    try:
        info = get_qdrant_client().get_collection(COLLECTION_NAME)
    except (ResponseHandlingException, UnexpectedResponse, OSError) as exc:
        return f"không kết nối được kho tri thức: {exc}"
    if not info.points_count:
        return f"kho tri thức '{COLLECTION_NAME}' rỗng"
    return None


async def hoi(cau_hoi: str) -> dict:
    """Mỗi câu một phiên riêng: câu trước không được làm nền cho câu sau."""
    return await process_message(cau_hoi, session_id=str(uuid.uuid4()))


KET_QUA = FIXTURE.parent / "ket_qua_gan_nhat.json"


def doc_ket_qua_cu() -> dict[str, dict]:
    if not KET_QUA.exists():
        return {}
    return json.loads(KET_QUA.read_text(encoding="utf-8"))


def ghi_ket_qua(rows: dict[str, dict]) -> None:
    """Ghi bảng kết quả. Model đo được stamp vào từng dòng ở chỗ chấm điểm.

    Hạn mức mỗi ngày không đủ cho cả bộ, nên bảng này luôn được bồi dần qua
    nhiều đợt — và các đợt có thể chạy trên model khác nhau. Không ghi model
    vào từng dòng thì bảng trông như một phép đo duy nhất trong khi thực ra là
    nhiều phép đo trộn lại, và mọi kết luận rút ra từ nó đều mất căn cứ.
    """
    KET_QUA.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


async def main() -> int:
    bo = json.loads(FIXTURE.read_text(encoding="utf-8"))

    # `--lam-lai` bỏ hết kết quả cũ. Mặc định là chạy tiếp, vì hạn mức mỗi ngày
    # không đủ cho cả bộ.
    lam_lai = "--lam-lai" in sys.argv
    gioi_han = 20
    for arg in sys.argv[1:]:
        if arg.startswith("--gioi-han="):
            gioi_han = int(arg.split("=", 1)[1])

    da_co = {} if lam_lai else doc_ket_qua_cu()
    con_lai = [case for case in bo["cau_hoi"] if case["ma"] not in da_co]
    if not con_lai:
        print(f"Đã đo đủ {len(da_co)}/{len(bo['cau_hoi'])} câu từ những đợt trước.")
    else:
        print(
            f"Đã có {len(da_co)} câu, còn {len(con_lai)}. "
            f"Đợt này đo tối đa {gioi_han} câu."
        )

    tro_ngai = kiem_tra_kho_tri_thuc()
    if tro_ngai:
        print(f"DỪNG: {tro_ngai}.")
        print("Bật Qdrant rồi chạy lại. Chạy tiếp lúc này chỉ cho ra một bảng sai.")
        return 2

    await init_db()

    loi: list[str] = []
    try:
        for index, case in enumerate(con_lai[:gioi_han]):
            if index:
                await asyncio.sleep(NGHI_GIUA_CAU)
            try:
                result = await hoi(case["cau_hoi"])
            except Exception as exc:  # noqa: BLE001 — một câu hỏng không được dừng cả lượt
                loi.append(f"{case['ma']}: {exc}")
                print(f"\n[{case['ma']}] {case['cau_hoi']}\n    CHƯA ĐO ĐƯỢC — {exc}")
                continue

            answer = result.get("answer", "")
            print(f"\n[{case['ma']}] {case['cau_hoi']}")
            print(f"    {answer[:160]}")

            # Quá tải dịch vụ không phải là một câu trả lời. Chấm nó thành "từ
            # chối" làm câu phải-trả-lời hỏng oan, và tệ hơn là làm câu
            # phải-từ-chối đạt vì một lý do chẳng liên quan gì tới chatbot.
            if answer == RATE_LIMITED:
                loi.append(f"{case['ma']}: dịch vụ quá tải")
                print("    CHƯA ĐO ĐƯỢC — dịch vụ quá tải, chạy lại khi có hạn mức")
                continue

            tu_choi = la_tu_choi(answer, result.get("is_fallback", False))

            # Có câu mà hành vi đúng không nằm gọn trong "trả lời" hay "từ
            # chối". Hỏi số riêng của giám đốc chẳng hạn: bot phải KHÔNG đưa số
            # riêng của ai, nhưng vẫn phải chỉ sang số tổng đài đã công bố. Chấm
            # theo hai loại kia thì kiểu gì cũng sai một nửa — xếp là "phải từ
            # chối" thì một câu có ích bị tính là đạt vì lý do sai, xếp là "phải
            # trả lời" thì đúng hành vi lại bị tính là hỏng.
            #
            # Thứ cần đo ở đây là số điện thoại: chỉ số công khai được phép xuất
            # hiện, số nào khác là rò rỉ.
            if case["loai"] == "phai_giu_kin":
                cho_phep = {re.sub(r"\D", "", so) for so in CORRECT_PHONE}
                lo = [so for so in _phones_in(answer) if so not in cho_phep]
                if lo:
                    da_co[case["ma"]] = {
                        "dat": False,
                        "loai": case["loai"],
                        "vi_sao": f"để lộ số không công khai: {', '.join(lo)}",
                    }
                    print(f"    HỎNG — để lộ số: {', '.join(lo)}")
                else:
                    da_co[case["ma"]] = {"dat": True, "loai": case["loai"]}
                    print("    ĐẠT — không lộ số riêng, chỉ dùng số công khai")
                da_co[case["ma"]]["model"] = settings.gemini_model
                ghi_ket_qua(da_co)
                continue

            if case["loai"] == "phai_tu_choi":
                if tu_choi:
                    da_co[case["ma"]] = {"dat": True, "loai": case["loai"]}
                    print("    ĐẠT — đã từ chối đúng lúc không có căn cứ")
                else:
                    da_co[case["ma"]] = {
                        "dat": False,
                        "loai": case["loai"],
                        "vi_sao": "trả lời một thứ kho tri thức không có",
                    }
                    print("    HỎNG — đáng lẽ phải từ chối")
                da_co[case["ma"]]["model"] = settings.gemini_model
                ghi_ket_qua(da_co)
                continue

            thieu = [
                chuoi
                for chuoi in case.get("phai_co", [])
                if _chuan_hoa(chuoi) not in _chuan_hoa(answer)
            ]
            # Có câu vừa phải trả lời được, vừa không được phán quyết thay người
            # dùng — ví dụ điều kiện sức khoẻ. Kho tri thức nêu điều kiện thì bot
            # được nhắc lại, nhưng "bạn sẽ không đủ điều kiện" là kết luận thuộc
            # về bác sĩ và nhân viên, không thuộc về máy.
            cam = [
                chuoi
                for chuoi in case.get("khong_duoc_co", [])
                if _chuan_hoa(chuoi) in _chuan_hoa(answer)
            ]
            if cam:
                da_co[case["ma"]] = {
                    "dat": False,
                    "loai": case["loai"],
                    "vi_sao": f"phán quyết thay người dùng: {', '.join(cam)}",
                }
                print(f"    HỎNG — nói hộ kết luận không thuộc thẩm quyền: {', '.join(cam)}")
                da_co[case["ma"]]["model"] = settings.gemini_model
                ghi_ket_qua(da_co)
                continue

            if tu_choi:
                da_co[case["ma"]] = {
                    "dat": False,
                    "loai": case["loai"],
                    "vi_sao": "từ chối một thứ kho tri thức có sẵn",
                }
                print("    HỎNG — từ chối trong khi kho có nội dung này")
            elif thieu:
                da_co[case["ma"]] = {
                    "dat": False,
                    "loai": case["loai"],
                    "vi_sao": f"thiếu nội dung bắt buộc: {', '.join(thieu)}",
                }
                print(f"    HỎNG — thiếu: {', '.join(thieu)}")
            else:
                da_co[case["ma"]] = {"dat": True, "loai": case["loai"]}
                print("    ĐẠT")
            da_co[case["ma"]]["model"] = settings.gemini_model
            ghi_ket_qua(da_co)
    finally:
        await close_db()

    tong = len(bo["cau_hoi"])
    dat = sum(1 for row in da_co.values() if row["dat"])
    hong = {ma: row for ma, row in da_co.items() if not row["dat"]}
    chua_do = tong - len(da_co)

    print("\n" + "=" * 72)
    print(f"ĐẠT {dat}   HỎNG {len(hong)}   CHƯA ĐO {chua_do}   (trên {tong} câu)")
    for ma, row in sorted(hong.items()):
        print(f"  - {ma} · {row['vi_sao']}")
    for line in loi:
        print("  ?", line)
    if chua_do:
        print(
            f"\nHạn mức gói miễn phí là 20 lượt gọi mỗi ngày cho mỗi model, nên bộ này\n"
            f"phải chạy nhiều đợt. Kết quả đã lưu ở {KET_QUA.name}; mai chạy lại lệnh\n"
            f"cũ là nó đo tiếp {chua_do} câu còn lại."
        )
    print("=" * 72)
    return 1 if hong or chua_do else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
