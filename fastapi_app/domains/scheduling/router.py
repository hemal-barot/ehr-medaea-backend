import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session

from backend.fastapi_app.core.database import get_db
from backend.fastapi_app.core.deps import get_current_active_user
from backend.fastapi_app.db.models import (
    Appointment, User, UserOrganization, Patient,
    PtoRequest, AvailabilityRule, ScheduleTemplate,
    Room, RoomBooking, StaffSchedule, OnCallAssignment,
)
from .schemas import (
    AppointmentCreate, AppointmentUpdate, AppointmentStatusUpdate, AppointmentResponse,
)

router = APIRouter(prefix="/appointments", tags=["Appointments"])
calendar_router = APIRouter(prefix="/calendar", tags=["Calendar"])


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_org_id(user: User, db: Session) -> Optional[str]:
    uo = db.query(UserOrganization).filter(UserOrganization.user_id == user.id).first()
    return uo.organization_id if uo else None


def _get_org_users(org_id: Optional[str], db: Session, limit: int = 20) -> List[User]:
    if org_id:
        uids = [r.user_id for r in db.query(UserOrganization)
                .filter(UserOrganization.organization_id == org_id).all()]
        return db.query(User).filter(User.id.in_(uids), User.is_active == True).all()
    return db.query(User).filter(User.is_active == True).limit(limit).all()


PALETTE = ["#0d9488", "#3b82f6", "#8b5cf6", "#f59e0b", "#ef4444", "#10b981", "#6366f1", "#ec4899"]


# ─── Appointments ─────────────────────────────────────────────────────────────

@router.get("", response_model=List[AppointmentResponse])
def list_appointments(
    status: Optional[str] = Query(None),
    date: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    q = db.query(Appointment).filter(Appointment.provider_id == current_user.id)
    if status:
        q = q.filter(Appointment.status == status)
    if date:
        try:
            d = datetime.strptime(date, "%Y-%m-%d")
            q = q.filter(
                Appointment.start_time >= d,
                Appointment.start_time < d + timedelta(days=1),
            )
        except ValueError:
            pass
    return q.order_by(Appointment.start_time).offset(skip).limit(limit).all()


@router.get("/me", response_model=List[AppointmentResponse])
def my_appointments(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(Appointment)
        .filter(Appointment.provider_id == current_user.id)
        .order_by(Appointment.start_time.desc())
        .limit(50)
        .all()
    )


@router.post("", response_model=AppointmentResponse, status_code=201)
def create_appointment(
    payload: AppointmentCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    org_id = _get_org_id(current_user, db)
    appt = Appointment(
        id=str(uuid.uuid4()),
        provider_id=current_user.id,
        organization_id=payload.organization_id or org_id,
        **payload.model_dump(exclude={"organization_id"}),
    )
    db.add(appt)
    db.commit()
    db.refresh(appt)
    return appt


@router.get("/{appt_id}", response_model=AppointmentResponse)
def get_appointment(
    appt_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    appt = db.query(Appointment).filter(Appointment.id == appt_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appt


@router.patch("/{appt_id}/status", response_model=AppointmentResponse)
def update_status(
    appt_id: str,
    payload: AppointmentStatusUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    appt = db.query(Appointment).filter(Appointment.id == appt_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    appt.status = payload.status
    db.commit()
    db.refresh(appt)
    return appt


@router.put("/{appt_id}", response_model=AppointmentResponse)
def update_appointment(
    appt_id: str,
    payload: AppointmentUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    appt = db.query(Appointment).filter(Appointment.id == appt_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(appt, field, value)
    db.commit()
    db.refresh(appt)
    return appt


@router.delete("/{appt_id}", status_code=204)
def delete_appointment(
    appt_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    appt = db.query(Appointment).filter(Appointment.id == appt_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    db.delete(appt)
    db.commit()


# ─── Calendar / Booking endpoints ─────────────────────────────────────────────

@calendar_router.get("/events", response_model=List[AppointmentResponse])
def calendar_events(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    q = db.query(Appointment).filter(Appointment.provider_id == current_user.id)
    if start:
        try:
            q = q.filter(Appointment.start_time >= datetime.fromisoformat(start))
        except ValueError:
            pass
    if end:
        try:
            q = q.filter(Appointment.start_time <= datetime.fromisoformat(end))
        except ValueError:
            pass
    return q.order_by(Appointment.start_time).all()


@calendar_router.get("/search-doctors")
def search_doctors(
    specialty: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(User).filter(User.is_active == True)
    if specialty:
        q = q.filter(User.specialty.ilike(f"%{specialty}%"))
    doctors = q.limit(20).all()
    return [
        {
            "id": d.id,
            "name": f"Dr. {d.first_name} {d.last_name or ''}".strip(),
            "specialty": d.specialty,
            "provider_type": d.provider_type,
        }
        for d in doctors
    ]


@calendar_router.get("/slots")
def available_slots(
    doctor_id: str = Query(...),
    booking_date: str = Query(...),
    db: Session = Depends(get_db),
):
    try:
        date = datetime.strptime(booking_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid date format, use YYYY-MM-DD")

    existing = (
        db.query(Appointment.start_time)
        .filter(
            Appointment.provider_id == doctor_id,
            Appointment.start_time >= date,
            Appointment.start_time < date + timedelta(days=1),
            Appointment.status != "cancelled",
        )
        .all()
    )
    booked_times = {a.start_time.strftime("%H:%M") for a in existing}
    slots = []
    current = date.replace(hour=8, minute=0)
    end = date.replace(hour=17, minute=0)
    while current < end:
        slot = current.strftime("%H:%M")
        if slot not in booked_times:
            slots.append(current.isoformat())
        current += timedelta(minutes=30)
    return slots


@calendar_router.post("/book-for-patient")
def book_for_patient(
    appointment_id: Optional[str] = Query(None),
    payload: AppointmentCreate = None,
    db: Session = Depends(get_db),
):
    if appointment_id:
        appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
        if appt:
            appt.status = "scheduled"
            db.commit()
            return {"message": "Appointment confirmed", "id": appt.id}
    appt = Appointment(
        id=str(uuid.uuid4()),
        patient_first_name=payload.patient_first_name if payload else "Unknown",
        patient_last_name=payload.patient_last_name if payload else "Patient",
        start_time=payload.start_time if payload else datetime.now(timezone.utc),
        status="scheduled",
    )
    db.add(appt)
    db.commit()
    return {"message": "Appointment booked", "id": appt.id}


@calendar_router.post("/upload-medical-docs/{appointment_id}")
async def upload_medical_docs(
    appointment_id: str,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    urls = [f"/uploads/{f.filename}" for f in files]
    return {"document_urls": urls}


# ─── Staff Schedule ────────────────────────────────────────────────────────────

@calendar_router.get("/staff")
def staff_schedule(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Return staff members with their weekly schedule from the staff_schedules table.
    Falls back to a generated schedule if no DB record exists for a user.
    """
    org_id = _get_org_id(current_user, db)
    users = _get_org_users(org_id, db)

    SHIFTS = ["7:00 AM - 3:00 PM", "8:00 AM - 5:00 PM", "9:00 AM - 6:00 PM", "12:00 PM - 8:00 PM"]
    result = []
    for i, u in enumerate(users):
        # Load schedule from DB
        sched = db.query(StaffSchedule).filter(StaffSchedule.user_id == u.id).first()
        if sched:
            schedule = {
                "mon": sched.mon or "Off",
                "tue": sched.tue or "Off",
                "wed": sched.wed or "Off",
                "thu": sched.thu or "Off",
                "fri": sched.fri or "Off",
                "sat": sched.sat or "Off",
                "sun": sched.sun or "Off",
            }
            status = sched.status or "active"
        else:
            # Generate deterministic schedule if no DB record
            schedule = {dk: SHIFTS[(i + di) % 4] if (i + di) % 5 != 3 else "Off"
                        for di, dk in enumerate(["mon", "tue", "wed", "thu", "fri"])}
            schedule.update({"sat": "Off", "sun": "Off"})
            status = "active"

        total = db.query(Appointment).filter(Appointment.provider_id == u.id).count()
        initials = ((u.first_name or "?")[0] + (u.last_name or "?")[0]).upper()
        result.append({
            "id": u.id,
            "name": f"Dr. {u.first_name} {u.last_name or ''}".strip(),
            "role": u.provider_type or "Physician",
            "specialty": u.specialty or "General Medicine",
            "initials": initials,
            "color": PALETTE[i % len(PALETTE)],
            "status": status,
            "totalAppts": total,
            "schedule": schedule,
        })
    return result


# ─── Clinic Calendar ──────────────────────────────────────────────────────────

@calendar_router.get("/clinic")
def clinic_calendar(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Return today's appointments formatted for the clinic day-view calendar."""
    org_id = _get_org_id(current_user, db)
    now = datetime.now(timezone.utc)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)

    q = db.query(Appointment)
    if org_id:
        q = q.filter(Appointment.organization_id == org_id)
    else:
        q = q.filter(Appointment.provider_id == current_user.id)

    appts = q.filter(
        Appointment.start_time >= day_start,
        Appointment.start_time < day_end,
    ).order_by(Appointment.start_time).all()

    result = []
    for a in appts:
        st = a.start_time
        duration = a.duration_minutes or 30
        end = st + timedelta(minutes=duration)
        provider = db.query(User).filter(User.id == a.provider_id).first() if a.provider_id else None
        result.append({
            "id": a.id,
            "patientName": f"{a.patient_first_name or ''} {a.patient_last_name or ''}".strip() or "Unknown Patient",
            "startTime": st.strftime("%H:%M"),
            "endTime": end.strftime("%H:%M"),
            "status": a.status or "scheduled",
            "type": a.visit_type or "Appointment",
            "room": a.room or "Room 1",
            "provider": f"Dr. {provider.first_name} {provider.last_name or ''}".strip() if provider else "Staff",
        })
    return result


# ─── On-Call Schedule ─────────────────────────────────────────────────────────

@calendar_router.get("/on-call")
def on_call_schedule(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Return on-call assignments from the on_call_assignments table."""
    org_id = _get_org_id(current_user, db)

    q = db.query(OnCallAssignment)
    if org_id:
        q = q.filter(OnCallAssignment.organization_id == org_id)

    assignments = q.order_by(OnCallAssignment.start_at).all()

    # If no assignments in DB yet, seed on the fly from active users
    if not assignments:
        users = _get_org_users(org_id, db, limit=10)
        PERIODS = [
            "Tonight 6 PM – 6 AM", "Tomorrow 8 AM – 8 PM",
            "This Weekend", "Next Monday – Friday",
        ]
        now = datetime.now(timezone.utc)
        for i, u in enumerate(users):
            backup = users[(i + 1) % len(users)] if len(users) > 1 else u
            oc = OnCallAssignment(
                id=str(uuid.uuid4()),
                user_id=u.id,
                organization_id=org_id,
                backup_user_id=backup.id,
                period_label=PERIODS[i % len(PERIODS)],
                start_at=now + timedelta(hours=i * 12),
                end_at=now + timedelta(hours=i * 12 + 12),
                status="active" if i % 3 != 2 else "upcoming",
                total_calls=0,
                emergencies=0,
            )
            db.add(oc)
        db.commit()
        assignments = q.order_by(OnCallAssignment.start_at).all()

    entries = []
    for i, oc in enumerate(assignments):
        u = db.query(User).filter(User.id == oc.user_id).first()
        if not u:
            continue
        backup = db.query(User).filter(User.id == oc.backup_user_id).first() if oc.backup_user_id else u
        initials = ((u.first_name or "?")[0] + (u.last_name or "?")[0]).upper()
        entries.append({
            "id": oc.id,
            "name": f"Dr. {u.first_name} {u.last_name or ''}".strip(),
            "initials": initials,
            "color": PALETTE[i % len(PALETTE)],
            "specialty": u.specialty or "General Medicine",
            "phone": u.phone or "+1 (555) 000-0000",
            "status": oc.status,
            "period": oc.period_label or "",
            "backup": f"Dr. {backup.first_name} {backup.last_name or ''}".strip() if backup else "TBD",
            "backupPhone": backup.phone or "+1 (555) 000-0001" if backup else "+1 (555) 000-0001",
            "totalCalls": oc.total_calls,
            "emergencies": oc.emergencies,
        })

    stats = {
        "active": sum(1 for e in entries if e["status"] == "active"),
        "upcoming": sum(1 for e in entries if e["status"] == "upcoming"),
        "totalCalls": sum(e["totalCalls"] for e in entries),
        "emergencies": sum(e["emergencies"] for e in entries),
        "physicians": len(entries),
    }
    return {"stats": stats, "entries": entries}


# ─── PTO / Blocked Time ───────────────────────────────────────────────────────

@calendar_router.get("/pto")
def list_pto(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    org_id = _get_org_id(current_user, db)
    q = db.query(PtoRequest)
    if org_id:
        q = q.filter(PtoRequest.organization_id == org_id)
    else:
        q = q.filter(PtoRequest.user_id == current_user.id)
    entries_db = q.order_by(PtoRequest.created_at.desc()).all()

    entries = []
    for e in entries_db:
        u = db.query(User).filter(User.id == e.user_id).first()
        if not u:
            continue
        initials = ((u.first_name or "?")[0] + (u.last_name or "?")[0]).upper()
        entries.append({
            "id": e.id,
            "name": f"Dr. {u.first_name} {u.last_name or ''}".strip(),
            "role": u.provider_type or "Physician",
            "initials": initials,
            "color": PALETTE[hash(u.id) % len(PALETTE)],
            "type": e.type,
            "status": e.status,
            "dateFrom": e.date_from,
            "dateTo": e.date_to,
            "duration": e.duration or "",
            "coverage": e.coverage_provider or "",
            "reason": e.reason or "",
        })

    stats = {
        "pto": sum(1 for e in entries if e["type"] == "PTO"),
        "sick": sum(1 for e in entries if e["type"] == "Sick"),
        "conference": sum(1 for e in entries if e["type"] == "Conference"),
        "blocked": sum(1 for e in entries if e["type"] == "Blocked"),
        "pending": sum(1 for e in entries if e["status"] == "pending"),
    }
    return {"stats": stats, "entries": entries}


@calendar_router.post("/pto", status_code=201)
def create_pto(body: dict, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    org_id = _get_org_id(current_user, db)
    pto = PtoRequest(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        organization_id=org_id,
        type=body.get("type", "PTO"),
        status=body.get("status", "pending"),
        date_from=body.get("dateFrom") or body.get("date_from", ""),
        date_to=body.get("dateTo") or body.get("date_to", ""),
        duration=body.get("duration", ""),
        coverage_provider=body.get("coverage") or body.get("coverage_provider", ""),
        reason=body.get("reason", ""),
    )
    db.add(pto)
    db.commit()
    db.refresh(pto)
    return {"id": pto.id, "status": pto.status, "type": pto.type}


@calendar_router.patch("/pto/{entry_id}/approve")
def approve_pto(entry_id: str, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    pto = db.query(PtoRequest).filter(PtoRequest.id == entry_id).first()
    if not pto:
        raise HTTPException(status_code=404, detail="PTO entry not found")
    pto.status = "approved"
    db.commit()
    return {"id": pto.id, "status": pto.status}


@calendar_router.patch("/pto/{entry_id}/deny")
def deny_pto(entry_id: str, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    pto = db.query(PtoRequest).filter(PtoRequest.id == entry_id).first()
    if not pto:
        raise HTTPException(status_code=404, detail="PTO entry not found")
    pto.status = "denied"
    db.commit()
    return {"id": pto.id, "status": pto.status}


# ─── Availability Rules ───────────────────────────────────────────────────────

@calendar_router.get("/rules")
def list_rules(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    org_id = _get_org_id(current_user, db)
    q = db.query(AvailabilityRule)
    if org_id:
        q = q.filter(
            (AvailabilityRule.organization_id == org_id) |
            (AvailabilityRule.organization_id == None)
        )
    rules = q.order_by(AvailabilityRule.priority, AvailabilityRule.created_at).all()
    rules_out = [
        {
            "id": r.id,
            "name": r.name,
            "type": r.type,
            "priority": r.priority,
            "description": r.description or "",
            "appliesTo": r.applies_to or "All Providers",
            "conditions": r.conditions or "",
            "enabled": r.enabled,
        }
        for r in rules
    ]
    stats = {
        "total": len(rules_out),
        "active": sum(1 for r in rules_out if r["enabled"]),
        "buffer": sum(1 for r in rules_out if r["type"] == "Buffer"),
        "conflict": sum(1 for r in rules_out if r["type"] in ("Conflict", "Double Booking")),
        "break": sum(1 for r in rules_out if r["type"] == "Break"),
    }
    return {"stats": stats, "rules": rules_out}


@calendar_router.post("/rules", status_code=201)
def create_rule(body: dict, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    org_id = _get_org_id(current_user, db)
    rule = AvailabilityRule(
        id=str(uuid.uuid4()),
        organization_id=org_id,
        name=body.get("name", "New Rule"),
        type=body.get("type", "Buffer"),
        priority=int(body.get("priority", 1)),
        description=body.get("description", ""),
        applies_to=body.get("appliesTo", "All Providers"),
        conditions=body.get("conditions", ""),
        enabled=True,
        created_by=current_user.id,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return {"id": rule.id, "name": rule.name, "type": rule.type, "enabled": rule.enabled}


@calendar_router.patch("/rules/{rule_id}/toggle")
def toggle_rule(rule_id: str, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    rule = db.query(AvailabilityRule).filter(AvailabilityRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    rule.enabled = not rule.enabled
    db.commit()
    return {"id": rule.id, "enabled": rule.enabled}


@calendar_router.delete("/rules/{rule_id}", status_code=204)
def delete_rule(rule_id: str, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    rule = db.query(AvailabilityRule).filter(AvailabilityRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    db.delete(rule)
    db.commit()


# ─── Schedule Templates ───────────────────────────────────────────────────────

@calendar_router.get("/templates")
def list_templates(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    org_id = _get_org_id(current_user, db)
    q = db.query(ScheduleTemplate)
    if org_id:
        q = q.filter(
            (ScheduleTemplate.organization_id == org_id) |
            (ScheduleTemplate.organization_id == None)
        )
    templates = q.order_by(ScheduleTemplate.created_at).all()
    templates_out = [
        {
            "id": t.id,
            "name": t.name,
            "badge": t.badge or "Provider",
            "status": t.status or "active",
            "description": t.description or "",
            "days": t.days or "Mon – Fri",
            "hours": t.hours or "8:00 AM – 5:00 PM",
            "types": t.types or "General",
            "appliedTo": t.applied_to or "All",
            "usageCount": t.usage_count or 0,
        }
        for t in templates
    ]
    stats = {
        "total": len(templates_out),
        "active": sum(1 for t in templates_out if t["status"] == "active"),
        "provider": sum(1 for t in templates_out if t["badge"] == "Provider"),
        "inUse": sum(1 for t in templates_out if t["usageCount"] > 0),
    }
    return {"stats": stats, "templates": templates_out}


@calendar_router.post("/templates", status_code=201)
def create_template(body: dict, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    org_id = _get_org_id(current_user, db)
    tmpl = ScheduleTemplate(
        id=str(uuid.uuid4()),
        organization_id=org_id,
        name=body.get("name", "New Template"),
        badge=body.get("badge", "Provider"),
        status="active",
        description=body.get("description", ""),
        days=body.get("days", "Mon – Fri"),
        hours=body.get("hours", "8:00 AM – 5:00 PM"),
        types=body.get("types", "General"),
        applied_to=body.get("appliedTo", "All"),
        usage_count=0,
        created_by=current_user.id,
    )
    db.add(tmpl)
    db.commit()
    db.refresh(tmpl)
    return {"id": tmpl.id, "name": tmpl.name, "status": tmpl.status}


@calendar_router.delete("/templates/{tmpl_id}", status_code=204)
def delete_template(tmpl_id: str, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    tmpl = db.query(ScheduleTemplate).filter(ScheduleTemplate.id == tmpl_id).first()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    db.delete(tmpl)
    db.commit()


# ─── Rooms & Room Bookings ────────────────────────────────────────────────────

@calendar_router.get("/rooms")
def list_rooms(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    org_id = _get_org_id(current_user, db)
    q = db.query(Room)
    if org_id:
        q = q.filter(
            (Room.organization_id == org_id) |
            (Room.organization_id == None)
        )
    rooms = q.all()

    # Today's bookings
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)
    room_ids = [r.id for r in rooms]
    bookings_db = (
        db.query(RoomBooking)
        .filter(
            RoomBooking.room_id.in_(room_ids),
            RoomBooking.booking_date >= today,
            RoomBooking.booking_date < tomorrow,
        )
        .all()
    )

    rooms_out = [
        {"id": r.id, "name": r.name, "type": r.type, "icon": r.icon or "fa-door-open", "status": r.status}
        for r in rooms
    ]
    bookings_out = [
        {
            "id": b.id,
            "roomId": b.room_id,
            "patientName": b.patient_name or "Unknown",
            "doctorName": b.doctor_name or "Staff",
            "startHour": b.start_hour,
            "startMin": b.start_min,
            "durationMin": b.duration_min,
        }
        for b in bookings_db
    ]
    stats = {
        "available": sum(1 for r in rooms_out if r["status"] == "available"),
        "inUse": sum(1 for r in rooms_out if r["status"] == "occupied"),
        "reserved": sum(1 for r in rooms_out if r["status"] == "reserved"),
        "maintenance": sum(1 for r in rooms_out if r["status"] == "maintenance"),
    }
    return {"stats": stats, "rooms": rooms_out, "bookings": bookings_out}
