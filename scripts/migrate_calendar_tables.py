"""
Migration: Calendar / Scheduling tables
- Adds duration_minutes, visit_type, room columns to appointments
- Creates: pto_requests, availability_rules, schedule_templates,
           rooms, room_bookings, staff_schedules, on_call_assignments
- Seeds baseline data for rules, templates, and rooms
"""
import os
import sys
import uuid
from datetime import datetime, timezone, timedelta

import psycopg2
from psycopg2.extras import execute_values

DB_URL = os.environ.get("DATABASE_URL", "")
if not DB_URL:
    # Fallback to individual vars
    DB_URL = "postgresql://{user}:{pw}@{host}/{db}?sslmode=disable".format(
        user=os.getenv("POSTGRES_USER", "postgres"),
        pw=os.getenv("POSTGRES_PASSWORD", "postgres"),
        host=os.getenv("POSTGRES_HOST", "localhost"),
        db=os.getenv("POSTGRES_DB", "medaea-v2"),
    )

conn = psycopg2.connect(DB_URL)
conn.autocommit = False
cur = conn.cursor()

print("Connected to DB. Running migrations…")

# ── 1. Appointments: add missing columns ─────────────────────────────────────
for col_def in [
    "ALTER TABLE appointments ADD COLUMN IF NOT EXISTS duration_minutes INTEGER DEFAULT 30",
    "ALTER TABLE appointments ADD COLUMN IF NOT EXISTS visit_type VARCHAR",
    "ALTER TABLE appointments ADD COLUMN IF NOT EXISTS room VARCHAR",
]:
    cur.execute(col_def)
    print(f"  ✓ appointments: {col_def.split('ADD COLUMN IF NOT EXISTS ')[1]}")

# ── 2. Create new tables ──────────────────────────────────────────────────────

cur.execute("""
CREATE TABLE IF NOT EXISTS pto_requests (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL REFERENCES users(id),
    organization_id VARCHAR REFERENCES organizations(id),
    type VARCHAR NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'pending',
    date_from VARCHAR NOT NULL,
    date_to VARCHAR NOT NULL,
    duration VARCHAR,
    coverage_provider VARCHAR,
    reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
)
""")
cur.execute("CREATE INDEX IF NOT EXISTS ix_pto_requests_user_id ON pto_requests(user_id)")
cur.execute("CREATE INDEX IF NOT EXISTS ix_pto_requests_org_id  ON pto_requests(organization_id)")
print("  ✓ pto_requests table ready")

cur.execute("""
CREATE TABLE IF NOT EXISTS availability_rules (
    id VARCHAR PRIMARY KEY,
    organization_id VARCHAR REFERENCES organizations(id),
    name VARCHAR NOT NULL,
    type VARCHAR NOT NULL,
    priority INTEGER DEFAULT 1,
    description TEXT,
    applies_to VARCHAR DEFAULT 'All Providers',
    conditions TEXT,
    enabled BOOLEAN DEFAULT TRUE,
    created_by VARCHAR REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
)
""")
cur.execute("CREATE INDEX IF NOT EXISTS ix_avail_rules_org ON availability_rules(organization_id)")
print("  ✓ availability_rules table ready")

cur.execute("""
CREATE TABLE IF NOT EXISTS schedule_templates (
    id VARCHAR PRIMARY KEY,
    organization_id VARCHAR REFERENCES organizations(id),
    name VARCHAR NOT NULL,
    badge VARCHAR DEFAULT 'Provider',
    status VARCHAR DEFAULT 'active',
    description TEXT,
    days VARCHAR,
    hours VARCHAR,
    types VARCHAR,
    applied_to VARCHAR,
    usage_count INTEGER DEFAULT 0,
    created_by VARCHAR REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
)
""")
cur.execute("CREATE INDEX IF NOT EXISTS ix_sched_tmpls_org ON schedule_templates(organization_id)")
print("  ✓ schedule_templates table ready")

cur.execute("""
CREATE TABLE IF NOT EXISTS rooms (
    id VARCHAR PRIMARY KEY,
    organization_id VARCHAR REFERENCES organizations(id),
    name VARCHAR NOT NULL,
    type VARCHAR,
    icon VARCHAR DEFAULT 'fa-door-open',
    status VARCHAR DEFAULT 'available',
    created_at TIMESTAMPTZ DEFAULT NOW()
)
""")
cur.execute("CREATE INDEX IF NOT EXISTS ix_rooms_org ON rooms(organization_id)")
print("  ✓ rooms table ready")

cur.execute("""
CREATE TABLE IF NOT EXISTS room_bookings (
    id VARCHAR PRIMARY KEY,
    room_id VARCHAR NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    appointment_id VARCHAR REFERENCES appointments(id),
    patient_name VARCHAR,
    doctor_name VARCHAR,
    booking_date TIMESTAMPTZ DEFAULT NOW(),
    start_hour INTEGER NOT NULL,
    start_min INTEGER DEFAULT 0,
    duration_min INTEGER DEFAULT 30,
    created_at TIMESTAMPTZ DEFAULT NOW()
)
""")
cur.execute("CREATE INDEX IF NOT EXISTS ix_room_bookings_room ON room_bookings(room_id)")
print("  ✓ room_bookings table ready")

cur.execute("""
CREATE TABLE IF NOT EXISTS staff_schedules (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL REFERENCES users(id),
    organization_id VARCHAR REFERENCES organizations(id),
    mon VARCHAR,
    tue VARCHAR,
    wed VARCHAR,
    thu VARCHAR,
    fri VARCHAR,
    sat VARCHAR DEFAULT 'Off',
    sun VARCHAR DEFAULT 'Off',
    status VARCHAR DEFAULT 'active',
    effective_from VARCHAR,
    created_at TIMESTAMPTZ DEFAULT NOW()
)
""")
cur.execute("CREATE INDEX IF NOT EXISTS ix_staff_sched_user ON staff_schedules(user_id)")
print("  ✓ staff_schedules table ready")

cur.execute("""
CREATE TABLE IF NOT EXISTS on_call_assignments (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL REFERENCES users(id),
    organization_id VARCHAR REFERENCES organizations(id),
    backup_user_id VARCHAR REFERENCES users(id),
    period_label VARCHAR,
    start_at TIMESTAMPTZ,
    end_at TIMESTAMPTZ,
    status VARCHAR DEFAULT 'upcoming',
    total_calls INTEGER DEFAULT 0,
    emergencies INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
)
""")
cur.execute("CREATE INDEX IF NOT EXISTS ix_on_call_user ON on_call_assignments(user_id)")
print("  ✓ on_call_assignments table ready")

# ── 3. Seed default availability rules (idempotent) ──────────────────────────
cur.execute("SELECT COUNT(*) FROM availability_rules")
if cur.fetchone()[0] == 0:
    rules = [
        (str(uuid.uuid4()), None, "15-Minute Buffer Between Appointments", "Buffer", 1,
         "Automatically adds 15 minutes buffer time between consecutive appointments.",
         "All Providers", "Consecutive appointments\nSame provider", True),
        (str(uuid.uuid4()), None, "No Double Booking", "Double Booking", 1,
         "Prevents scheduling two appointments at the same time for the same provider.",
         "All Providers", "Overlapping time slots\nSame provider", True),
        (str(uuid.uuid4()), None, "Lunch Break Block (12–1 PM)", "Break", 2,
         "Blocks 12:00 PM – 1:00 PM for all providers every weekday.",
         "All Staff", "12:00 PM – 1:00 PM\nMonday – Friday", True),
        (str(uuid.uuid4()), None, "72-Hour Advance Booking", "Advance", 3,
         "Requires appointments to be scheduled at least 72 hours in advance.",
         "New Patients", "Booking window ≥ 72 hours\nNew patient type", False),
    ]
    execute_values(cur,
        """INSERT INTO availability_rules
           (id, organization_id, name, type, priority, description, applies_to, conditions, enabled)
           VALUES %s""",
        rules)
    print(f"  ✓ Seeded {len(rules)} availability rules")
else:
    print("  – availability_rules already has data, skipping seed")

# ── 4. Seed default schedule templates ───────────────────────────────────────
cur.execute("SELECT COUNT(*) FROM schedule_templates")
if cur.fetchone()[0] == 0:
    templates = [
        (str(uuid.uuid4()), None, "Standard Physician Schedule", "Provider", "active",
         "Mon–Fri, 8 AM–5 PM with 30-minute appointment slots.",
         "Monday – Friday", "8:00 AM – 5:00 PM\n(30-min slots)",
         "New Patient, Follow-up, Telehealth", "General Medicine", 12),
        (str(uuid.uuid4()), None, "Cardiology Clinic Template", "Department", "active",
         "Extended hours with 45-minute slots for complex cardiac workups.",
         "Mon, Tue, Thu, Fri", "7:00 AM – 6:00 PM\n(45-min slots)",
         "Consultation, Procedure, Follow-up", "Cardiology Dept", 5),
        (str(uuid.uuid4()), None, "Urgent Care Block", "Clinic", "active",
         "Walk-in and urgent care slots, 7 days a week.",
         "Monday – Sunday", "8:00 AM – 8:00 PM\n(15-min slots)",
         "Urgent, Walk-in", "Urgent Care Wing", 3),
    ]
    execute_values(cur,
        """INSERT INTO schedule_templates
           (id, organization_id, name, badge, status, description, days, hours, types, applied_to, usage_count)
           VALUES %s""",
        templates)
    print(f"  ✓ Seeded {len(templates)} schedule templates")
else:
    print("  – schedule_templates already has data, skipping seed")

# ── 5. Seed default rooms ─────────────────────────────────────────────────────
cur.execute("SELECT COUNT(*) FROM rooms")
if cur.fetchone()[0] == 0:
    rooms = [
        (str(uuid.uuid4()), None, "Exam Room 1",        "General",    "fa-door-open",    "available"),
        (str(uuid.uuid4()), None, "Exam Room 2",        "General",    "fa-door-open",    "occupied"),
        (str(uuid.uuid4()), None, "Procedure Room A",   "Procedure",  "fa-plus-square",  "reserved"),
        (str(uuid.uuid4()), None, "Cardiology Suite",   "Specialty",  "fa-heartbeat",    "available"),
        (str(uuid.uuid4()), None, "Consultation Room 1","Consult",    "fa-comments",     "occupied"),
        (str(uuid.uuid4()), None, "Lab / Imaging",      "Diagnostic", "fa-microscope",   "maintenance"),
    ]
    execute_values(cur,
        "INSERT INTO rooms (id, organization_id, name, type, icon, status) VALUES %s",
        rooms)
    print(f"  ✓ Seeded {len(rooms)} rooms")

    # Seed room bookings for the occupied rooms
    cur.execute("SELECT id FROM rooms WHERE status = 'occupied' OR status = 'reserved' LIMIT 3")
    occupied = [r[0] for r in cur.fetchall()]
    today = datetime.now(timezone.utc).replace(hour=9, minute=0, second=0, microsecond=0)
    bookings_data = [
        (str(uuid.uuid4()), occupied[0] if len(occupied) > 0 else rooms[1][0],
         "John Smith", "Dr. Sarah Chen", today, 9, 0, 30),
        (str(uuid.uuid4()), occupied[1] if len(occupied) > 1 else rooms[2][0],
         "Maria Garcia", "Dr. Marcus Lee", today, 10, 30, 60),
        (str(uuid.uuid4()), occupied[2] if len(occupied) > 2 else rooms[4][0],
         "Robert Johnson", "Dr. Priya Patel", today, 11, 0, 45),
    ]
    execute_values(cur,
        """INSERT INTO room_bookings
           (id, room_id, patient_name, doctor_name, booking_date, start_hour, start_min, duration_min)
           VALUES %s""",
        bookings_data)
    print(f"  ✓ Seeded {len(bookings_data)} room bookings")
else:
    print("  – rooms already has data, skipping seed")

# ── 6. Seed staff_schedules for existing users ───────────────────────────────
cur.execute("SELECT COUNT(*) FROM staff_schedules")
if cur.fetchone()[0] == 0:
    cur.execute("SELECT id FROM users WHERE is_active = TRUE LIMIT 20")
    users = [r[0] for r in cur.fetchall()]
    SHIFTS = ["7:00 AM - 3:00 PM", "8:00 AM - 5:00 PM", "9:00 AM - 6:00 PM", "12:00 PM - 8:00 PM"]
    sched_rows = []
    for i, uid in enumerate(users):
        sched_rows.append((
            str(uuid.uuid4()), uid, None,
            SHIFTS[i % 4],           # mon
            SHIFTS[(i+1) % 4],       # tue
            SHIFTS[(i+2) % 4],       # wed
            "Off" if i % 4 == 3 else SHIFTS[(i+3) % 4],  # thu
            SHIFTS[(i+1) % 4],       # fri
            "Off", "Off",            # sat, sun
            "active", "2026-01-01",
        ))
    if sched_rows:
        execute_values(cur,
            """INSERT INTO staff_schedules
               (id, user_id, organization_id, mon, tue, wed, thu, fri, sat, sun, status, effective_from)
               VALUES %s""",
            sched_rows)
        print(f"  ✓ Seeded {len(sched_rows)} staff schedules")
    else:
        print("  – no users found to seed schedules")
else:
    print("  – staff_schedules already has data, skipping seed")

# ── 7. Seed on_call_assignments for existing users ───────────────────────────
cur.execute("SELECT COUNT(*) FROM on_call_assignments")
if cur.fetchone()[0] == 0:
    cur.execute("SELECT id FROM users WHERE is_active = TRUE LIMIT 10")
    users = [r[0] for r in cur.fetchall()]
    PERIODS = [
        ("Tonight 6 PM – 6 AM",    0, 24),
        ("Tomorrow 8 AM – 8 PM",   24, 36),
        ("This Weekend",           48, 96),
        ("Next Monday – Friday",   120, 240),
    ]
    now = datetime.now(timezone.utc)
    oc_rows = []
    for i, uid in enumerate(users):
        p = PERIODS[i % len(PERIODS)]
        backup_uid = users[(i + 1) % len(users)] if len(users) > 1 else uid
        oc_rows.append((
            str(uuid.uuid4()), uid, None, backup_uid,
            p[0],
            now + timedelta(hours=p[1]),
            now + timedelta(hours=p[2]),
            "active" if i % 3 != 2 else "upcoming",
            0, 0,
        ))
    if oc_rows:
        execute_values(cur,
            """INSERT INTO on_call_assignments
               (id, user_id, organization_id, backup_user_id, period_label, start_at, end_at, status, total_calls, emergencies)
               VALUES %s""",
            oc_rows)
        print(f"  ✓ Seeded {len(oc_rows)} on-call assignments")
    else:
        print("  – no users found to seed on-call assignments")
else:
    print("  – on_call_assignments already has data, skipping seed")

conn.commit()
cur.close()
conn.close()
print("\nMigration complete ✓")
