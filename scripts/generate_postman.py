#!/usr/bin/env python3
"""
Medaea EHR — Postman Collection Generator
==========================================
Reads the FastAPI OpenAPI schema + manually-defined Django/extra endpoints,
then writes:
  postman/Medaea_EHR_API.postman_collection.json
  postman/Medaea_EHR_Dev.postman_environment.json
  postman/Medaea_EHR_QA.postman_environment.json
  postman/Medaea_EHR_Prod.postman_environment.json

Run any time a route is added or modified:
  python3 backend/scripts/generate_postman.py
"""
import json
import os
import sys
import uuid
from pathlib import Path

# ── make sure project root is on the path ────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from backend.fastapi_app.main import app as fastapi_app

# ═══════════════════════════════════════════════════════════════════════════════
#  CONFIG — edit here to customise the collection
# ═══════════════════════════════════════════════════════════════════════════════

COLLECTION_NAME = "Medaea EHR API"
FASTAPI_PREFIX   = "/api/v1"   # strip this when building url parts
POSTMAN_OUT      = ROOT / "postman"

# Tag → emoji display name (order controls folder order in the collection)
TAG_DISPLAY = {
    "Authentication":   "🔐 Authentication",
    "Users":            "👤 Users",
    "Organizations":    "🏢 Organizations",
    "Patients":         "🧑‍⚕️ Patients",
    "Appointments":     "📅 Appointments",
    "Calendar":         "🗓️ Calendar",
    "Encounters":       "🏥 Encounters",
    "Clinical Charting":"🩺 Clinical Charting",
    "Audit":            "📝 Audit Logs",
    "System":           "⚙️ System",
    # Add new FastAPI tags here as you create them
}

# Calendar path-prefix → sub-folder name (order matters)
CALENDAR_SUBFOLDERS = {
    "/api/v1/calendar/pto":       "🏖️ PTO / Leave",
    "/api/v1/calendar/rules":     "⚙️ Scheduling Rules",
    "/api/v1/calendar/templates": "📋 Schedule Templates",
    "/api/v1/calendar/rooms":     "🚪 Rooms",
    # Any /calendar/* not matched above stays in the root Calendar folder
}

# No-auth endpoints (path fragments) — these won't receive an Authorization header
NO_AUTH_PATHS = {
    "/auth/signup", "/auth/login", "/auth/forgot-password", "/auth/reset-password",
    "/auth/verify-email", "/auth/resend-verification", "/auth/mfa/verify",
    "/api/health",
}

# ── Smart example values for well-known field names ──────────────────────────
FIELD_EXAMPLES = {
    "email": "{{loginEmail}}",
    "password": "{{loginPassword}}",
    "new_password": "NewPass123!",
    "current_password": "{{loginPassword}}",
    "first_name": "Jane",
    "last_name": "Doe",
    "phone": "+15550001234",
    "role": "doctor",
    "specialty": "General Medicine",
    "organization_name": "Test Clinic",
    "hipaa_consent": True,
    "patient_id": "{{patientId}}",
    "provider_id": "{{currentUserId}}",
    "organization_id": "{{orgId}}",
    "patient_first_name": "John",
    "patient_last_name": "Smith",
    "start_time": "2026-04-15T09:00:00Z",
    "end_time": "2026-04-15T09:30:00Z",
    "duration_minutes": 30,
    "visit_type": "Follow-up",
    "reason": "Routine check-up",
    "status": "active",
    "location": "Room 1",
    "location_type": "in-person",
    "date_of_birth": "1980-05-15",
    "gender": "M",
    "address": "123 Main St",
    "city": "Chicago",
    "state": "IL",
    "zip": "60601",
    "mrn": "MRN-001",
    "encounter_type": "office_visit",
    "chief_complaint": "Routine visit",
    "subjective": "Patient reports no acute complaints.",
    "objective": "Vitals stable. BP 120/80.",
    "assessment": "Healthy adult.",
    "plan": "Continue current management.",
    "allergen": "Penicillin",
    "allergen_type": "drug",
    "reaction": "Hives",
    "severity": "moderate",
    "name": "Lisinopril",
    "dosage": "10mg",
    "frequency": "Once daily",
    "route": "Oral",
    "rxnorm_code": "203644",
    "description": "Hypertension",
    "icd10_code": "I10",
    "chronic": True,
    "vaccine_name": "Influenza",
    "cvx_code": "141",
    "date_administered": "2026-01-15",
    "dose_number": 1,
    "lot_number": "LT2026A",
    "method": "authenticator",
    "code": "{{mfaCode}}",
    "token": "{{resetToken}}",
    "setup_token": "{{mfaSetupToken}}",
    "mfa_token": "{{mfaLoginToken}}",
    "dateFrom": "2026-05-01",
    "dateTo": "2026-05-05",
    "date_from": "2026-05-01",
    "date_to": "2026-05-05",
    "duration": "5 days",
    "coverage": "Dr. James Park",
    "type": "PTO",
    "priority": 1,
    "conditions": "Between appointments",
    "appliesTo": "All Providers",
    "badge": "Provider",
    "days": "Monday – Friday",
    "hours": "8:00 AM – 5:00 PM",
    "types": "New Patient, Follow-up",
    "appliedTo": "General Medicine",
    "icon": "fa-door-open",
    "npi": "1234567890",
    "booking_date": "2026-04-15",
    "doctor_id": "{{currentUserId}}",
    "backup_user_id": "{{currentUserId}}",
    "period_label": "Tonight 6 PM – 6 AM",
}

# ── Manual body overrides for endpoints that accept body: dict (no Pydantic schema) ──
# Key = "METHOD /full/openapi/path"
BODY_OVERRIDES: dict[str, dict] = {
    "POST /api/v1/calendar/pto": {
        "type": "PTO",
        "dateFrom": "2026-05-01",
        "dateTo": "2026-05-05",
        "duration": "5 days",
        "reason": "Family vacation",
        "coverage": "Dr. James Park",
    },
    "POST /api/v1/calendar/rules": {
        "name": "New Custom Rule",
        "type": "Buffer",
        "priority": 2,
        "description": "Custom buffer rule",
        "appliesTo": "All Providers",
        "conditions": "Between appointments",
    },
    "POST /api/v1/calendar/templates": {
        "name": "Afternoon Clinic Block",
        "badge": "Provider",
        "description": "PM clinic sessions",
        "days": "Monday – Friday",
        "hours": "1:00 PM – 6:00 PM",
        "types": "Follow-up, Telehealth",
        "appliedTo": "Internal Medicine",
    },
    "POST /api/v1/calendar/book-for-patient": {
        "patient_first_name": "Maria",
        "patient_last_name": "Garcia",
        "start_time": "2026-04-15T10:00:00Z",
        "provider_id": "{{currentUserId}}",
        "reason": "Initial consultation",
    },
}

# ── Test scripts attached to specific path fragments ─────────────────────────
TEST_SCRIPTS = {
    "/auth/login": """
pm.test("Status 200", () => pm.response.to.have.status(200));
pm.test("Has access_token", () => pm.expect(pm.response.json()).to.have.property("access_token"));
if (pm.response.code === 200) {
    const res = pm.response.json();
    if (res.access_token) {
        pm.environment.set("authToken", res.access_token);
        console.log("✅ authToken saved");
    }
    if (res.user && res.user.id) pm.environment.set("currentUserId", res.user.id);
}
""",
    "/auth/signup": """
pm.test("Status 201", () => pm.response.to.have.status(201));
""",
    "/patients": """
if (pm.response.code === 201) {
    const res = pm.response.json();
    if (res.id) pm.environment.set("patientId", res.id);
}
if (pm.response.code === 200) {
    const arr = pm.response.json();
    if (Array.isArray(arr) && arr.length) pm.environment.set("patientId", arr[0].id);
}
""",
    "/appointments": """
if (pm.response.code === 201) {
    const res = pm.response.json();
    if (res.id) pm.environment.set("appointmentId", res.id);
}
if (pm.response.code === 200) {
    const arr = pm.response.json();
    if (Array.isArray(arr) && arr.length) pm.environment.set("appointmentId", arr[0].id);
}
""",
    "/encounters": """
if (pm.response.code === 201) {
    const res = pm.response.json();
    if (res.id) pm.environment.set("encounterId", res.id);
}
if (pm.response.code === 200) {
    const arr = pm.response.json();
    if (Array.isArray(arr) && arr.length) pm.environment.set("encounterId", arr[0].id);
}
""",
    "/users/me": """
pm.test("Status 200", () => pm.response.to.have.status(200));
const res = pm.response.json();
if (res.id) pm.environment.set("currentUserId", res.id);
""",
    "/organizations/my-organizations": """
pm.test("Status 200", () => pm.response.to.have.status(200));
const arr = pm.response.json();
if (Array.isArray(arr) && arr.length) pm.environment.set("orgId", arr[0].id);
""",
    "/calendar/pto": """
if (pm.response.code === 200) {
    const res = pm.response.json();
    if (res.entries && res.entries.length) pm.environment.set("ptoId", res.entries[0].id);
}
if (pm.response.code === 201) {
    const res = pm.response.json();
    if (res.id) pm.environment.set("ptoId", res.id);
}
""",
    "/calendar/rules": """
if (pm.response.code === 200) {
    const res = pm.response.json();
    if (res.rules && res.rules.length) pm.environment.set("ruleId", res.rules[0].id);
}
if (pm.response.code === 201) {
    const res = pm.response.json();
    if (res.id) pm.environment.set("ruleId", res.id);
}
""",
    "/calendar/templates": """
if (pm.response.code === 200) {
    const res = pm.response.json();
    if (res.templates && res.templates.length) pm.environment.set("templateId", res.templates[0].id);
}
if (pm.response.code === 201) {
    const res = pm.response.json();
    if (res.id) pm.environment.set("templateId", res.id);
}
""",
    "/calendar/rooms": """
pm.test("Status 200", () => pm.response.to.have.status(200));
const res = pm.response.json();
if (res.rooms && res.rooms.length) pm.environment.set("roomId", res.rooms[0].id);
""",
    "/allergies": """
if (pm.response.code === 201) {
    const res = pm.response.json();
    if (res.id) pm.environment.set("allergyId", res.id);
}
""",
}

# ═══════════════════════════════════════════════════════════════════════════════
#  DJANGO / EXTRA ENDPOINTS
#  Add new entries here whenever a Django REST endpoint is created.
#  Format mirrors a simplified OpenAPI operation object.
# ═══════════════════════════════════════════════════════════════════════════════
DJANGO_ENDPOINTS = [
    # {
    #   "tag": "Django Admin API",         # folder name
    #   "method": "GET",
    #   "path": "/django/api/v1/example",  # full path (no base URL)
    #   "name": "Example Endpoint",
    #   "description": "...",
    #   "body": {"key": "value"},          # optional request body dict
    #   "params": {"filter": "active"},    # optional query params
    #   "no_auth": False,
    # },
]


# ═══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _uid() -> str:
    return str(uuid.uuid4())


def _resolve_ref(ref: str, components: dict) -> dict:
    """Follow a $ref pointer into components/schemas."""
    parts = ref.lstrip("#/").split("/")
    node = {"components": components}
    for p in parts:
        node = node.get(p, {})
    return node


def _schema_to_example(schema: dict, components: dict, depth: int = 0) -> object:
    """Recursively build a sensible example value from an OpenAPI schema."""
    if depth > 5:
        return None
    if not schema:
        return None

    if "$ref" in schema:
        schema = _resolve_ref(schema["$ref"], components)

    # anyOf / oneOf → use first
    for combiner in ("anyOf", "oneOf"):
        if combiner in schema:
            options = [s for s in schema[combiner] if s.get("type") != "null"]
            if options:
                return _schema_to_example(options[0], components, depth + 1)

    if "example" in schema:
        return schema["example"]
    if "default" in schema:
        return schema["default"]

    t = schema.get("type", "object")

    if t == "object" or "properties" in schema:
        obj = {}
        for prop, prop_schema in schema.get("properties", {}).items():
            if prop in FIELD_EXAMPLES:
                obj[prop] = FIELD_EXAMPLES[prop]
            else:
                obj[prop] = _schema_to_example(prop_schema, components, depth + 1)
        return obj

    if t == "array":
        item_ex = _schema_to_example(schema.get("items", {}), components, depth + 1)
        return [item_ex] if item_ex is not None else []

    if t == "string":
        fmt = schema.get("format", "")
        if fmt == "date-time":
            return "2026-04-15T09:00:00Z"
        if fmt == "date":
            return "2026-04-15"
        if fmt == "email":
            return "user@example.com"
        if fmt == "password":
            return "SecurePass123!"
        return schema.get("enum", [None])[0] or ""

    if t == "integer":
        return schema.get("minimum", 1)
    if t == "number":
        return float(schema.get("minimum", 1.0))
    if t == "boolean":
        return True

    return None


def _pm_path(openapi_path: str):
    """Convert /api/v1/patients/{patient_id} → Postman URL object."""
    raw = "{{baseUrl}}" + openapi_path
    segments = openapi_path.lstrip("/").split("/")
    pm_segments = []
    pm_vars = []
    for seg in segments:
        if seg.startswith("{") and seg.endswith("}"):
            var_name = seg[1:-1]
            pm_segments.append(":" + var_name)
            pm_vars.append({"key": var_name, "value": "{{" + var_name + "}}"})
        else:
            pm_segments.append(seg)
    return raw, pm_segments, pm_vars


def _get_test_script(path: str) -> str | None:
    for fragment, script in TEST_SCRIPTS.items():
        if fragment in path:
            return script
    return None


def _build_request(method: str, path: str, operation: dict, components: dict) -> dict:
    """Convert a single OpenAPI operation → Postman request item."""
    summary = operation.get("summary", "") or operation.get("operationId", "")
    name = summary or (method.upper() + " " + path.replace("/api/v1", ""))

    # ── URL ──────────────────────────────────────────────────────────────────
    raw_url, pm_segments, pm_vars = _pm_path(path)
    query_params = []
    for param in operation.get("parameters", []):
        if param.get("in") == "query":
            ex = param.get("example", param.get("schema", {}).get("example", ""))
            query_params.append({
                "key": param["name"],
                "value": str(ex) if ex else "",
                "description": param.get("description", ""),
                "disabled": not param.get("required", False),
            })

    url_obj = {
        "raw": raw_url + ("?" + "&".join(f"{p['key']}={p['value']}" for p in query_params if not p["disabled"]) if query_params else ""),
        "host": ["{{baseUrl}}"],
        "path": pm_segments,
        "variable": pm_vars,
        "query": query_params,
    }

    # ── Headers ───────────────────────────────────────────────────────────────
    headers = [{"key": "Content-Type", "value": "application/json"}]
    no_auth = any(frag in path for frag in NO_AUTH_PATHS)
    if not no_auth:
        headers.append({"key": "Authorization", "value": "Bearer {{authToken}}", "type": "text"})

    # ── Body ──────────────────────────────────────────────────────────────────
    body = None
    override_key = f"{method.upper()} {path}"
    rb = operation.get("requestBody", {})
    if rb:
        content = rb.get("content", {})
        schema = (content.get("application/json", {}) or content.get("*/*", {})).get("schema", {})
        if schema:
            # Use manual override if schema is a bare dict (additionalProperties: true)
            is_bare_dict = schema.get("additionalProperties") is True and not schema.get("properties")
            if is_bare_dict and override_key in BODY_OVERRIDES:
                example_val = BODY_OVERRIDES[override_key]
            else:
                example_val = _schema_to_example(schema, components)
            if example_val is not None:
                body = {
                    "mode": "raw",
                    "raw": json.dumps(example_val, indent=2),
                    "options": {"raw": {"language": "json"}},
                }
        elif content.get("multipart/form-data") or content.get("application/x-www-form-urlencoded"):
            body = {"mode": "formdata", "formdata": []}

    # ── Test script ────────────────────────────────────────────────────────────
    script = _get_test_script(path)
    events = []
    if script:
        events.append({
            "listen": "test",
            "script": {"type": "text/javascript", "exec": script.strip().split("\n")},
        })

    item = {
        "_postman_id": _uid(),
        "name": name,
        "request": {
            "method": method.upper(),
            "header": headers,
            "url": url_obj,
            "description": operation.get("description", ""),
        },
        "response": [],
    }
    if body:
        item["request"]["body"] = body
    if events:
        item["event"] = events

    return item


def _build_django_request(ep: dict) -> dict:
    """Build a Postman request item from a manually-specified Django endpoint."""
    path = ep["path"]
    method = ep["method"].upper()
    raw_url, pm_segments, pm_vars = _pm_path(path)

    query_params = [{"key": k, "value": str(v), "disabled": False}
                    for k, v in (ep.get("params") or {}).items()]

    url_obj = {
        "raw": raw_url,
        "host": ["{{djangoBaseUrl}}"],
        "path": pm_segments,
        "variable": pm_vars,
        "query": query_params,
    }

    headers = [{"key": "Content-Type", "value": "application/json"}]
    if not ep.get("no_auth"):
        headers.append({"key": "Authorization", "value": "Bearer {{djangoToken}}", "type": "text"})

    body = None
    if ep.get("body"):
        body = {
            "mode": "raw",
            "raw": json.dumps(ep["body"], indent=2),
            "options": {"raw": {"language": "json"}},
        }

    item = {
        "_postman_id": _uid(),
        "name": ep.get("name", method + " " + path),
        "request": {
            "method": method,
            "header": headers,
            "url": url_obj,
            "description": ep.get("description", ""),
        },
        "response": [],
    }
    if body:
        item["request"]["body"] = body
    return item


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN BUILDER
# ═══════════════════════════════════════════════════════════════════════════════

def build_collection() -> dict:
    schema = fastapi_app.openapi()
    paths = schema.get("paths", {})
    components = schema.get("components", {})

    # ── Group paths by tag ────────────────────────────────────────────────────
    tag_buckets: dict[str, list] = {tag: [] for tag in TAG_DISPLAY}
    untagged: list = []

    # Preferred HTTP method ordering within a path
    METHOD_ORDER = ["get", "post", "put", "patch", "delete", "options", "head"]

    for path, path_item in sorted(paths.items()):
        for method in METHOD_ORDER:
            operation = path_item.get(method)
            if not operation or not isinstance(operation, dict):
                continue
            tags = operation.get("tags", [])
            tag = tags[0] if tags else "Untagged"
            item = _build_request(method, path, operation, components)

            if tag in tag_buckets:
                tag_buckets[tag].append((path, item))
            else:
                # New tag not yet in TAG_DISPLAY — create a new folder automatically
                if tag not in tag_buckets:
                    tag_buckets[tag] = []
                    TAG_DISPLAY[tag] = tag  # use as-is
                tag_buckets[tag].append((path, item))

    # ── Build Calendar sub-folders ────────────────────────────────────────────
    def _calendar_subfolder(items_with_path: list) -> list:
        sub_buckets: dict[str, list] = {}  # sub-folder name → [item]
        root_items: list = []

        for path, item in items_with_path:
            matched = False
            for prefix, sf_name in CALENDAR_SUBFOLDERS.items():
                if path.startswith(prefix):
                    sub_buckets.setdefault(sf_name, []).append(item)
                    matched = True
                    break
            if not matched:
                root_items.append(item)

        result = list(root_items)
        for sf_name in CALENDAR_SUBFOLDERS.values():  # preserve defined order
            if sf_name in sub_buckets:
                result.append({
                    "_postman_id": _uid(),
                    "name": sf_name,
                    "item": sub_buckets[sf_name],
                })
        return result

    # ── Assemble folders ──────────────────────────────────────────────────────
    folders = []
    for tag, display_name in TAG_DISPLAY.items():
        bucket = tag_buckets.get(tag, [])
        if not bucket:
            continue

        if tag == "Calendar":
            items = _calendar_subfolder(bucket)
        else:
            items = [item for _, item in bucket]

        folders.append({
            "_postman_id": _uid(),
            "name": display_name,
            "item": items,
        })

    # ── Django / extra endpoints ──────────────────────────────────────────────
    if DJANGO_ENDPOINTS:
        django_buckets: dict[str, list] = {}
        for ep in DJANGO_ENDPOINTS:
            tag = ep.get("tag", "Django Admin API")
            django_buckets.setdefault(tag, []).append(_build_django_request(ep))
        for tag, items in django_buckets.items():
            folders.append({
                "_postman_id": _uid(),
                "name": f"🛠️ {tag}",
                "item": items,
            })

    # ── Count totals ──────────────────────────────────────────────────────────
    def _count(items):
        n = 0
        for i in items:
            if "item" in i:
                n += _count(i["item"])
            elif "request" in i:
                n += 1
        return n

    total = _count(folders)

    return {
        "info": {
            "_postman_id": _uid(),
            "name": COLLECTION_NAME,
            "description": (
                f"Auto-generated from FastAPI OpenAPI spec + Django endpoints.\n"
                f"Total: **{total} requests** across {len(folders)} feature folders.\n\n"
                f"**Quick start:**\n"
                f"1. Select an environment (Dev / QA / Prod)\n"
                f"2. Run **Login** — `authToken` is captured automatically\n"
                f"3. All other requests use `{{{{authToken}}}}` from the environment\n\n"
                f"_Regenerate: `python3 backend/scripts/generate_postman.py`_"
            ),
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
            "version": {"major": 1, "minor": 0, "patch": 0},
        },
        "auth": {
            "type": "bearer",
            "bearer": [{"key": "token", "value": "{{authToken}}", "type": "string"}],
        },
        "variable": [
            {"key": "baseUrl",       "value": "http://localhost:8000", "type": "string"},
            {"key": "authToken",     "value": "",                      "type": "string"},
            {"key": "currentUserId", "value": "",                      "type": "string"},
            {"key": "orgId",         "value": "",                      "type": "string"},
            {"key": "patientId",     "value": "",                      "type": "string"},
            {"key": "appointmentId", "value": "",                      "type": "string"},
            {"key": "encounterId",   "value": "",                      "type": "string"},
            {"key": "ptoId",         "value": "",                      "type": "string"},
            {"key": "ruleId",        "value": "",                      "type": "string"},
            {"key": "templateId",    "value": "",                      "type": "string"},
            {"key": "roomId",        "value": "",                      "type": "string"},
            {"key": "allergyId",     "value": "",                      "type": "string"},
        ],
        "item": folders,
    }


def build_environment(name: str, base_url: str,
                      login_email: str = "doc@medaea.com",
                      login_password: str = "TestPass123!",
                      django_base_url: str = "",
                      django_token: str = "") -> dict:
    suffix = name.lower()
    return {
        "id": _uid(),
        "name": f"Medaea EHR — {name}",
        "_postman_variable_scope": "environment",
        "values": [
            # ── FastAPI ────────────────────────────────────────────────────────
            {"key": "baseUrl",       "value": base_url,         "type": "default", "enabled": True},
            {"key": "loginEmail",    "value": login_email,      "type": "default", "enabled": True},
            {"key": "loginPassword", "value": login_password,   "type": "secret",  "enabled": True},
            {"key": "authToken",     "value": "",               "type": "secret",  "enabled": True},
            # ── Django Admin API ───────────────────────────────────────────────
            {"key": "djangoBaseUrl", "value": django_base_url,  "type": "default", "enabled": True},
            {"key": "djangoToken",   "value": django_token,     "type": "secret",  "enabled": True},
            # ── Auth flow helpers ──────────────────────────────────────────────
            {"key": "signupEmail",    "value": f"newdoc+{suffix}@test.com", "type": "default", "enabled": True},
            {"key": "signupPassword", "value": "TestPass123!",  "type": "secret",  "enabled": True},
            {"key": "resetToken",     "value": "",              "type": "default", "enabled": True},
            {"key": "verifyToken",    "value": "",              "type": "default", "enabled": True},
            {"key": "mfaCode",        "value": "",              "type": "default", "enabled": True},
            {"key": "mfaSetupToken",  "value": "",              "type": "default", "enabled": True},
            {"key": "mfaLoginToken",  "value": "",              "type": "default", "enabled": True},
            # ── Resource IDs (auto-populated by test scripts) ─────────────────
            {"key": "currentUserId",  "value": "",              "type": "default", "enabled": True},
            {"key": "orgId",          "value": "",              "type": "default", "enabled": True},
            {"key": "patientId",      "value": "",              "type": "default", "enabled": True},
            {"key": "appointmentId",  "value": "",              "type": "default", "enabled": True},
            {"key": "encounterId",    "value": "",              "type": "default", "enabled": True},
            {"key": "ptoId",          "value": "",              "type": "default", "enabled": True},
            {"key": "ruleId",         "value": "",              "type": "default", "enabled": True},
            {"key": "templateId",     "value": "",              "type": "default", "enabled": True},
            {"key": "roomId",         "value": "",              "type": "default", "enabled": True},
            {"key": "allergyId",      "value": "",              "type": "default", "enabled": True},
        ],
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    POSTMAN_OUT.mkdir(parents=True, exist_ok=True)

    print("📦  Reading FastAPI OpenAPI schema…")
    collection = build_collection()

    col_path = POSTMAN_OUT / "Medaea_EHR_API.postman_collection.json"
    with open(col_path, "w") as f:
        json.dump(collection, f, indent=2)

    # Count total requests
    def _count(items):
        n = 0
        for i in items:
            if "item" in i: n += _count(i["item"])
            elif "request" in i: n += 1
        return n
    total = _count(collection["item"])
    folders = len(collection["item"])
    print(f"✅  Collection written: {col_path.name} ({total} requests, {folders} folders)")

    envs = [
        build_environment("Dev",  "http://localhost:8000",
                          django_base_url="http://localhost:9000"),
        build_environment("QA",   "https://qa-api.medaea.com",
                          login_email="qa@medaea.com",
                          login_password="QaTest123!",
                          django_base_url="https://qa-admin.medaea.com"),
        build_environment("Prod", "https://api.medaea.com",
                          login_email="",
                          login_password="",
                          django_base_url="https://admin.medaea.com"),
    ]
    env_names = ["Dev", "QA", "Prod"]
    for env_data, env_name in zip(envs, env_names):
        env_path = POSTMAN_OUT / f"Medaea_EHR_{env_name}.postman_environment.json"
        with open(env_path, "w") as f:
            json.dump(env_data, f, indent=2)
        print(f"✅  Environment written: {env_path.name}")

    print(f"\n📁  Output folder: {POSTMAN_OUT}")
    print("\nFolder breakdown:")
    for folder in collection["item"]:
        n = _count(folder.get("item", []))
        print(f"   {folder['name']}: {n} requests")


if __name__ == "__main__":
    main()
