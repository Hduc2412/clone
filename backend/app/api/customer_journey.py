from fastapi import APIRouter, Depends, HTTPException

from app.auth.security import get_current_user
from app.db.database import get_managed_lead, list_recruitment_applications
from app.services.customer_journey_service import get_customer_journey


router = APIRouter(
    prefix="/management/leads",
    tags=["Customer journey"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/{lead_code}/journey")
async def customer_journey(lead_code: str, current_user=Depends(get_current_user)):
    lead = await get_managed_lead(lead_code)
    if lead is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy khách hàng.")
    if current_user["role"] == "consultant":
        email = current_user["email"].strip().lower()
        applications = await list_recruitment_applications(
            lead_code=lead_code, assigned_to=email, limit=1
        )
        lead_owner = (lead.get("assigned_to") or "").strip().lower()
        if lead_owner != email and not applications:
            raise HTTPException(
                status_code=403, detail="Bạn chỉ được xem khách hàng được giao cho mình."
            )
        return await get_customer_journey(lead, appointment_owner=email)
    return await get_customer_journey(lead)
