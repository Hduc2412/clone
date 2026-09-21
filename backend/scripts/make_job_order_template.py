"""Sinh file Excel chủ để doanh nghiệp nhập danh mục đơn tuyển dụng.

    python -m scripts.make_job_order_template
    python -m scripts.make_job_order_template --output "F:/duong/dan/File.xlsx"

Mặc định ghi ra `Tailieu/DonHang/MauDonHang_ChuDe.xlsx`. File này cũng tải được
từ màn hình quản trị, nhưng sinh sẵn ra thư mục tài liệu để gửi cho doanh nghiệp
trước khi hệ thống được triển khai.
"""
import argparse
from pathlib import Path

from app.services.job_order_import import build_template_workbook


BACKEND_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = BACKEND_DIR.parent.parent / "Tailieu" / "DonHang" / "MauDonHang_ChuDe.xlsx"


def main() -> None:
    parser = argparse.ArgumentParser(description="Sinh file Excel mẫu đơn tuyển dụng.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--no-samples",
        action="store_true",
        help="Không kèm sheet dữ liệu ví dụ.",
    )
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    workbook = build_template_workbook(include_samples=not args.no_samples)
    workbook.save(args.output)
    print(f"Đã ghi file mẫu: {args.output}")


if __name__ == "__main__":
    main()
