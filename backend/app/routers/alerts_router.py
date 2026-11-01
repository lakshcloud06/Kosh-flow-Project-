from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.schemas import AlertItem
from app.auth import get_current_user
from app.services import real_data

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get("", response_model=List[AlertItem])
def get_alerts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Alerts for the top notification bar, built live from real cash and forecast (High and Medium risk)."""
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    items = []
    for r in real_data.atm_risk_table(db):
        if r["risk_level"] not in ("high", "medium"):
            continue
        days = r["days_left"]
        who = f"{r['atm_id']} ({r['city']})"
        if days <= 0.3:
            msg = f"{who} critical: predicted to run out in less than 6 hours."
        elif days <= 1.0:
            msg = f"{who} predicted to run out of cash tomorrow."
        else:
            msg = f"{who} cash level low: ~{days:.1f} days remaining."
        items.append(AlertItem(id=len(items) + 1, atm_id=r["atm_id"], message=msg,
                               risk_level=r["risk_level"], cash_left=r["cash_left"],
                               predicted_runout_days=days, created_at=now))

    # High risk first, then the ones closest to running out
    items.sort(key=lambda x: (0 if x.risk_level == "high" else 1, x.predicted_runout_days))
    for i, it in enumerate(items, start=1):
        it.id = i
    return items
