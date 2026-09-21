"""Nạp danh mục đơn tuyển dụng mẫu vào MongoDB.

    python -m scripts.seed_job_orders           # thêm mới hoặc cập nhật theo mã đơn
    python -m scripts.seed_job_orders --reset   # xóa đơn mẫu cũ rồi nạp lại
    python -m scripts.seed_job_orders --dry-run # chỉ in ra, không ghi

Đơn mẫu mang mã cố định `DH-0001`…`DH-0019` nên chạy lại nhiều lần không sinh
bản trùng. Sau khi nạp, bộ đếm mã được đẩy lên qua khoảng đã dùng để đơn thật
do nhân viên nhập tiếp tục từ `DH-0020` chứ không đè lên đơn mẫu.

Đơn mẫu được đánh dấu `created_by = "seed"` để lệnh `--reset` biết cái nào là dữ
liệu mẫu mà xóa, không đụng vào đơn thật của doanh nghiệp.
"""
import argparse
import asyncio
from datetime import timedelta
from typing import Any

from app.core.timeutil import local_today
from app.db.common import get_db, now
from app.db.database import close_db, init_db
from app.db.job_orders import COLLECTION, COUNTER_COLLECTION
from app.matching import catalog
from scripts.seed_data.job_orders_seed import JOB_ORDERS_SEED


SEED_MARKER = "seed"


def _require(value: object, normalizer, label: str, code: str) -> str:
    normalized = normalizer(value)
    if normalized is None:
        raise ValueError(f"{code}: {label} không hợp lệ: {value!r}")
    return normalized


def build_document(entry: dict[str, Any], index: int) -> dict[str, Any]:
    """Đưa một mục dữ liệu mẫu về đúng hình dạng bản ghi trong database."""
    code = f"DH-{index:04d}"
    today = local_today()
    prefecture = _require(
        entry["prefecture"], catalog.normalize_prefecture, "Tỉnh", code
    )
    interview_in_days = entry.get("interview_in_days")
    timestamp = now()

    document: dict[str, Any] = {
        "code": code,
        "title": entry["title"],
        "employer_name": entry["employer_name"],
        "employer_type": _require(
            entry["employer_type"], catalog.normalize_employer_type, "Loại hình cơ sở", code
        ),
        "program": _require(
            entry["program"], catalog.normalize_program, "Diện chương trình", code
        ),
        "prefecture": prefecture,
        "region_group": catalog.region_for_prefecture(prefecture),
        "city": entry.get("city"),
        "quota": entry["quota"],
        "hired_count": 0,
        "deadline": (today + timedelta(days=entry["deadline_in_days"])).isoformat(),
        "requirements": {
            "japanese_required": _require(
                entry["japanese_required"],
                catalog.normalize_japanese_level,
                "Trình độ tiếng Nhật",
                code,
            ),
            "education_required": (
                _require(
                    entry["education_required"],
                    catalog.normalize_education,
                    "Bằng cấp yêu cầu",
                    code,
                )
                if entry.get("education_required")
                else None
            ),
            "experience_min": float(entry.get("experience_min", 0)),
            "age_min": entry.get("age_min"),
            "age_max": entry.get("age_max"),
            "gender_pref": _require(
                entry.get("gender_pref", "khong_yeu_cau"),
                catalog.normalize_gender_pref,
                "Yêu cầu giới tính",
                code,
            ),
        },
        "reference": {
            "salary_min": entry.get("salary_min"),
            "salary_max": entry.get("salary_max"),
            "allowances": entry.get("allowances", []),
            "cost_total_vnd": entry.get("cost_total_vnd"),
            "interview_date": (
                (today + timedelta(days=interview_in_days)).isoformat()
                if interview_in_days is not None
                else None
            ),
            "departure_expected": entry.get("departure_expected"),
            "highlights": entry.get("highlights", []),
        },
        "description": entry.get("description"),
        "internal_note": entry.get("internal_note"),
        "status": _require(
            entry.get("status", "draft"),
            catalog.normalize_job_order_status,
            "Trạng thái",
            code,
        ),
        "published": bool(entry.get("published", False)),
        "created_by": SEED_MARKER,
        "updated_by": SEED_MARKER,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    _validate(document)
    return document


def _validate(document: dict[str, Any]) -> None:
    """Bắt lỗi dữ liệu mẫu ngay lúc dựng, thay vì để lộ ra khi demo."""
    code = document["code"]
    requirements = document["requirements"]
    reference = document["reference"]
    if document["quota"] < 1:
        raise ValueError(f"{code}: số lượng tuyển phải lớn hơn 0.")
    age_min, age_max = requirements["age_min"], requirements["age_max"]
    if age_min is not None and age_max is not None and age_min > age_max:
        raise ValueError(f"{code}: tuổi tối thiểu lớn hơn tuổi tối đa.")
    salary_min, salary_max = reference["salary_min"], reference["salary_max"]
    if salary_min is not None and salary_max is not None and salary_min > salary_max:
        raise ValueError(f"{code}: lương tối thiểu lớn hơn lương tối đa.")
    if document["region_group"] is None:
        raise ValueError(f"{code}: không suy được vùng từ tỉnh {document['prefecture']}.")


def build_documents() -> list[dict[str, Any]]:
    return [
        build_document(entry, index)
        for index, entry in enumerate(JOB_ORDERS_SEED, start=1)
    ]


def summarize(documents: list[dict[str, Any]]) -> dict[str, Any]:
    today = local_today().isoformat()
    visible = [
        document
        for document in documents
        if document["published"]
        and document["status"] == "open"
        and document["deadline"] >= today
    ]
    return {
        "tong_so": len(documents),
        "hien_cong_khai": len(visible),
        "theo_vung": sorted({document["region_group"] for document in documents}),
        "theo_chuong_trinh": sorted({document["program"] for document in documents}),
        "theo_loai_hinh": sorted({document["employer_type"] for document in documents}),
        "muc_tieng_nhat": sorted(
            {document["requirements"]["japanese_required"] for document in documents}
        ),
    }


async def seed(reset: bool = False, dry_run: bool = False) -> dict[str, Any]:
    documents = build_documents()
    report = summarize(documents)
    if dry_run:
        return report | {"da_ghi": 0}

    await init_db()
    try:
        collection = get_db()[COLLECTION]
        if reset:
            deleted = await collection.delete_many({"created_by": SEED_MARKER})
            report["da_xoa"] = deleted.deleted_count

        written = 0
        for document in documents:
            await collection.update_one(
                {"code": document["code"]},
                {
                    "$set": {
                        key: value
                        for key, value in document.items()
                        if key != "created_at"
                    },
                    "$setOnInsert": {"created_at": document["created_at"]},
                },
                upsert=True,
            )
            written += 1

        # Đẩy bộ đếm qua khoảng mã đã dùng cho dữ liệu mẫu, để đơn thật nhập sau
        # không nhận trùng mã rồi bị unique index chặn.
        await get_db()[COUNTER_COLLECTION].update_one(
            {"_id": COLLECTION},
            {"$max": {"seq": len(documents)}},
            upsert=True,
        )
        report["da_ghi"] = written
    finally:
        await close_db()
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Nạp đơn tuyển dụng mẫu.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Xóa đơn mẫu đã nạp trước đó rồi nạp lại.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Chỉ kiểm tra và in thống kê, không ghi vào database.",
    )
    args = parser.parse_args()

    report = asyncio.run(seed(reset=args.reset, dry_run=args.dry_run))
    print("Kết quả nạp đơn tuyển dụng mẫu")
    for key, value in report.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
