"""
Behave step definitions for appointment scheduling scenarios.
"""
import requests
from behave import given, when, then
from datetime import date, timedelta


def api_url(context, path):
    base = getattr(context, "base_url", "http://localhost:8000")
    today = date.today().isoformat()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    next_week = (date.today() + timedelta(days=7)).isoformat()
    in_10 = (date.today() + timedelta(days=10)).isoformat()
    in_12 = (date.today() + timedelta(days=12)).isoformat()

    path = (
        path.replace("{today}", today)
            .replace("{tomorrow}", tomorrow)
            .replace("{next_week}", next_week)
            .replace("{in_10_days}", in_10)
            .replace("{in_12_days}", in_12)
            .replace("{patient_id}", str(getattr(context, "patient_id", 0)))
    )
    return f"{base}{path}"


@given("a patient exists for scheduling tests")
def step_scheduling_patient(context):
    resp = requests.post(
        api_url(context, "/api/v1/patients"),
        json={
            "first_name": "Scheduling",
            "last_name": "TestPatient",
            "date_of_birth": "1980-05-10",
            "gender": "male",
            "email": "sched.bdd@patient.test",
            "phone": "555-0400",
            "address": "4 Sched St",
            "city": "Boston",
            "state": "MA",
            "zip_code": "02104",
        },
        headers=getattr(context, "auth_headers", {}),
    )
    context.patient_id = resp.json().get("id")


@when('I POST to "{path}" with:')
def step_post_with_table(context, path):
    row = context.table[0]
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    in_10 = (date.today() + timedelta(days=10)).isoformat()
    in_12 = (date.today() + timedelta(days=12)).isoformat()

    body = {}
    for key in row.headings:
        val = row[key]
        val = val.replace("{tomorrow}", tomorrow).replace("{in_10_days}", in_10).replace("{in_12_days}", in_12)
        try:
            body[key] = int(val)
        except ValueError:
            body[key] = val

    if "patient_id" not in body and hasattr(context, "patient_id"):
        body["patient_id"] = context.patient_id

    context.response = requests.post(
        api_url(context, path),
        json=body,
        headers=getattr(context, "auth_headers", {}),
    )


@when('I POST to "{path}" with an empty body')
def step_post_empty(context, path):
    context.response = requests.post(
        api_url(context, path),
        json={},
        headers=getattr(context, "auth_headers", {}),
    )
