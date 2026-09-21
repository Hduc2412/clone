"""Đăng ký sơ bộ: ứng viên tự chọn đơn rồi xác nhận.

## Chốt chặn: không tạo đăng ký từ suy đoán của máy

Ứng viên chỉ đăng ký được **đơn đã thật sự được giới thiệu cho chính họ và đã đạt
điều kiện bắt buộc**. Mã đơn gửi lên được đối chiếu ngược với nhật ký giới thiệu
gần nhất của hồ sơ đó; không có trong nhật ký thì từ chối.

Nghe thừa, vì giao diện chỉ hiện những đơn đã giới thiệu. Nhưng giao diện không
phải là hàng rào — ai cũng gửi được một mã đơn bất kỳ lên đường công khai này. Và
quan trọng hơn: kiểm tra ngược như vậy biến câu "hệ thống không tự quyết thay ứng
viên" từ một lời hứa trong tài liệu thành một điều kiện có thật trong mã nguồn.

## Ba thứ được tạo cùng lúc

1. **Khách hàng** (nếu số điện thoại này chưa có) — để nhân viên có chỗ ghi lịch
   sử liên hệ.
2. **Hồ sơ đăng ký** ở trạng thái `draft`, chưa giao cho ai — đây chính là mục
   nằm trong hàng đợi.
3. **Phiếu tóm tắt tư vấn** — bản chụp mọi thứ nhân viên cần đọc trước khi gọi.

Thứ tự này không đảo được: phiếu trỏ tới hồ sơ đăng ký, hồ sơ đăng ký trỏ tới
khách hàng.
"""
from typing import Any

from pymongo.errors import DuplicateKeyError

from app.core.codes import PREFIX_APPLICATION, PREFIX_LEAD, PREFIX_REPORT, new_code
from app.db import candidate_documents as documents
from app.db import candidate_profiles as profiles
from app.db import consultation_reports as reports
from app.db import recommendation_logs as logs
from app.db.database import (
    REFERENCE_APPLICATION,
    create_application_event,
    create_managed_lead,
    create_notification,
    create_recruitment_application,
    get_managed_lead_by_phone,
    update_recruitment_application,
)
from app.services import matching_service, report_builder


SOURCE_SELF = "self_registration"
INITIAL_STATUS = "draft"


class RegistrationRejected(Exception):
    """Không tạo được đăng ký. Thông điệp viết cho ứng viên đọc."""


class AlreadyRegistered(Exception):
    """Ứng viên này đang có một hồ sơ đăng ký còn hoạt động."""


async def register(*, session_id: str, job_order_code: str) -> dict[str, Any]:
    profile = await profiles.get_by_session(session_id)
    if profile is None:
        raise RegistrationRejected("Chưa có hồ sơ cho phiên này.")
    if profile.get("status") != profiles.STATUS_CONFIRMED:
        raise RegistrationRejected(
            "Bạn cần xem lại và xác nhận hồ sơ trước khi đăng ký đơn."
        )

    phone = ((profile.get("fields") or {}).get("phone") or {}).get("value")
    if not phone:
        raise RegistrationRejected(
            "Bạn để lại số điện thoại giúp mình, để nhân viên gọi lại tư vấn nhé."
        )

    full_name = ((profile.get("fields") or {}).get("full_name") or {}).get("value") or "Ứng viên"

    # Tra nhật ký đúng một lần rồi truyền đi. Gọi lại nhiều lần thì mỗi lần có
    # thể ra một bản khác nhau, và hồ sơ đăng ký sẽ trỏ tới một nhật ký không
    # phải cái vừa dùng để kiểm tra.
    log = await _latest_log(profile)
    item = _recommended_item(log, job_order_code)
    profiles.decorate(profile)

    lead = await _ensure_lead(full_name=full_name, phone=phone)
    application_code = new_code(PREFIX_APPLICATION)

    try:
        application = await create_recruitment_application(
            {
                "application_code": application_code,
                "lead_code": lead["lead_code"],
                "customer_name": lead["customer_name"],
                "phone": lead["phone"],
                # Chưa giao cho ai. Chính chỗ `None` này khiến bản ghi nằm trong
                # hàng đợi chờ nhân viên nhận.
                "assigned_to": None,
                "status": INITIAL_STATUS,
                "is_active": True,
                "source": SOURCE_SELF,
                "profile_code": profile["code"],
                "session_id": session_id,
                "job_order_code": item["code"],
                "job_order_title": item.get("title"),
                "match_score": item.get("score"),
                "recommendation_log_code": log["code"],
                "japanese_level": (
                    (profile.get("labels") or {}).get("japanese_level")
                ),
                "destination": item.get("prefecture"),
                "report_code": None,
            }
        )
    except DuplicateKeyError as exc:
        raise AlreadyRegistered(
            "Bạn đang có một hồ sơ đăng ký đang được xử lý. "
            "Nhân viên sẽ liên hệ để trao đổi thêm nhé."
        ) from exc

    report = await _create_report(
        profile=profile,
        item=item,
        application_code=application_code,
        session_id=session_id,
    )
    application = (
        await update_recruitment_application(
            application_code, {"report_code": report["code"]}
        )
        or application
    )

    await profiles.attach_lead(profile["code"], lead["lead_code"], lead["phone"])
    await logs.attach_application(log["code"], application_code)
    await create_application_event(
        {
            "application_code": application_code,
            "action": "self_registered",
            "actor_email": None,
            "actor_name": full_name,
            "details": {
                "job_order_code": item["code"],
                "match_score": item.get("score"),
                "report_code": report["code"],
            },
        }
    )
    # Đẩy sang hệ thống nội bộ kèm thông báo. Hàng đợi là nơi nhân viên chủ động
    # vào xem; thông báo là thứ đi tìm họ khi họ đang làm việc khác.
    await create_notification(
        notification_type="new_registration",
        title="Ứng viên mới đăng ký đơn",
        reference_type=REFERENCE_APPLICATION,
        reference_code=application_code,
        detail={
            "customer_name": lead["customer_name"],
            "job_order_code": item["code"],
            "job_order_title": item.get("title"),
        },
    )
    return {"application": application, "report": report}


async def _latest_log(profile: dict[str, Any]) -> dict[str, Any]:
    log = await logs.latest_for_profile(profile["code"])
    if log is None:
        raise RegistrationRejected(
            "Bạn xem danh sách đơn phù hợp trước đã, rồi chọn một đơn để đăng ký nhé."
        )
    return log


def _recommended_item(log: dict[str, Any], job_order_code: str) -> dict[str, Any]:
    """Đơn được chọn phải nằm trong nhật ký giới thiệu và phải đủ điều kiện."""
    for row in log.get("items") or ():
        if row.get("code") == job_order_code:
            if not row.get("eligible"):
                raise RegistrationRejected(
                    "Đơn này hiện chưa đạt điều kiện bắt buộc với hồ sơ của bạn. "
                    "Bạn chọn một đơn khác trong danh sách phù hợp giúp mình nhé."
                )
            return row
    raise RegistrationRejected(
        "Đơn này không có trong danh sách đã giới thiệu cho bạn. "
        "Bạn chọn lại từ danh sách giúp mình nhé."
    )


async def _ensure_lead(*, full_name: str, phone: str) -> dict[str, Any]:
    """Dùng lại khách hàng cũ nếu số điện thoại đã có trong hệ thống.

    Tạo mới vô điều kiện sẽ đâm vào index duy nhất theo số điện thoại, và tệ hơn
    là cắt đứt hồ sơ mới khỏi lịch sử liên hệ trước đó của chính người ấy.
    """
    existing = await get_managed_lead_by_phone(phone)
    if existing is not None:
        return existing
    return await create_managed_lead(
        {
            "lead_code": new_code(PREFIX_LEAD),
            "customer_name": full_name,
            "phone": phone,
            "source": SOURCE_SELF,
            "status": "new",
            "assigned_to": None,
            "note": "Ứng viên tự đăng ký qua kênh tư vấn tự động.",
        }
    )


async def _create_report(
    *,
    profile: dict[str, Any],
    item: dict[str, Any],
    application_code: str,
    session_id: str,
) -> dict[str, Any]:
    enriched = matching_service.public_item(item)
    attachments = await documents.list_for_profile(profile["code"])
    content = report_builder.build(
        profile=profile,
        order_item=enriched,
        explanation_block=enriched.get("explanation_block", ""),
        documents=attachments,
    )
    return await reports.create(
        {
            "code": new_code(PREFIX_REPORT),
            "application_code": application_code,
            "profile_code": profile["code"],
            "session_id": session_id,
            "job_order_code": item["code"],
            **content,
        }
    )
