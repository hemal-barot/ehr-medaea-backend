"""
Behave step definitions for patient management scenarios.
"""
import requests
from behave import given, when, then


def api_url(context, path):
    base = getattr(context, "base_url", "http://localhost:8000")
    return f"{base}{path}"


@when('I GET "{path}"')
def step_get(context, path):
    path = path.replace("{patient_id}", str(getattr(context, "patient_id", 0)))
    context.response = requests.get(
        api_url(context, path),
        headers=getattr(context, "auth_headers", {}),
    )


@when('I POST to "{path}" with patient details:')
def step_post_patient(context, path):
    row = context.table[0]
    context.response = requests.post(
        api_url(context, path),
        json={
            "first_name": row["first_name"],
            "last_name": row["last_name"],
            "date_of_birth": row["date_of_birth"],
            "gender": row["gender"],
            "email": row["email"],
            "phone": "555-0300",
            "address": "1 Test Ave",
            "city": "Boston",
            "state": "MA",
            "zip_code": "02103",
        },
        headers=getattr(context, "auth_headers", {}),
    )
    if context.response.status_code in (200, 201):
        context.patient_id = context.response.json().get("id")


@given('a patient exists with first name "{first_name}" and last name "{last_name}"')
def step_create_patient(context, first_name, last_name):
    resp = requests.post(
        api_url(context, "/api/v1/patients"),
        json={
            "first_name": first_name,
            "last_name": last_name,
            "date_of_birth": "1970-01-01",
            "gender": "unknown",
            "email": f"{first_name.lower()}.{last_name.lower()}@bdd.test",
            "phone": "555-0000",
            "address": "0 BDD St",
            "city": "Boston",
            "state": "MA",
            "zip_code": "02100",
        },
        headers=getattr(context, "auth_headers", {}),
    )
    context.patient_id = resp.json().get("id")


@then("the response body should be a JSON array")
def step_check_array(context):
    data = context.response.json()
    assert isinstance(data, list), f"Expected list, got: {type(data)}"


@then('the response body should include "{field}"')
def step_check_body_field(context, field):
    data = context.response.json()
    assert field in data, f"Field '{field}' missing from response: {data}"


@then('the response body should include "{field}" equal to "{value}"')
def step_check_body_value(context, field, value):
    data = context.response.json()
    assert str(data.get(field)) == value, f"Expected {field}={value}, got {data.get(field)}"


@then('the patient\'s last name should be "{last_name}"')
def step_check_patient_last_name(context, last_name):
    data = context.response.json()
    assert data.get("last_name") == last_name
