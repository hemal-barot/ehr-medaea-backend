"""
Tests for appointment + scheduling endpoints:
  GET  /api/v1/appointments/me
  POST /api/v1/appointments
  GET  /api/v1/appointments/{id}
  GET  /api/v1/calendar/events
  GET  /api/v1/calendar/slots
"""
import pytest
from datetime import date, timedelta


def _create_patient(client, auth_headers):
    resp = client.post("/api/v1/patients", json={
        "first_name": "Sched",
        "last_name": "Patient",
        "date_of_birth": "1990-01-01",
        "gender": "male",
        "email": "sched.patient@test.com",
        "phone": "555-0200",
        "address": "456 Elm St",
        "city": "Boston",
        "state": "MA",
        "zip_code": "02102",
    }, headers=auth_headers)
    return resp.json()["id"]


def test_list_my_appointments_requires_auth(client):
    resp = client.get("/api/v1/appointments/me")
    assert resp.status_code == 401


def test_list_my_appointments(client, auth_headers):
    resp = client.get("/api/v1/appointments/me", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_create_appointment(client, auth_headers):
    patient_id = _create_patient(client, auth_headers)
    tomorrow = (date.today() + timedelta(days=1)).isoformat()

    resp = client.post("/api/v1/appointments", json={
        "patient_id": patient_id,
        "appointment_date": tomorrow,
        "appointment_time": "09:00",
        "duration_minutes": 30,
        "visit_type": "office_visit",
        "notes": "Annual checkup",
    }, headers=auth_headers)
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert "id" in data
    assert data["patient_id"] == patient_id


def test_create_appointment_missing_fields(client, auth_headers):
    resp = client.post("/api/v1/appointments", json={}, headers=auth_headers)
    assert resp.status_code == 422


def test_get_appointment_by_id(client, auth_headers):
    patient_id = _create_patient(client, auth_headers)
    tomorrow = (date.today() + timedelta(days=2)).isoformat()

    create_resp = client.post("/api/v1/appointments", json={
        "patient_id": patient_id,
        "appointment_date": tomorrow,
        "appointment_time": "10:00",
        "duration_minutes": 60,
        "visit_type": "telehealth",
    }, headers=auth_headers)
    appt_id = create_resp.json()["id"]

    resp = client.get(f"/api/v1/appointments/{appt_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == appt_id


def test_calendar_events_endpoint(client, auth_headers):
    today = date.today().isoformat()
    next_week = (date.today() + timedelta(days=7)).isoformat()

    resp = client.get(
        f"/api/v1/calendar/events?start={today}&end={next_week}",
        headers=auth_headers,
    )
    assert resp.status_code == 200


def test_calendar_slots_endpoint(client, auth_headers):
    tomorrow = (date.today() + timedelta(days=1)).isoformat()

    resp = client.get(
        f"/api/v1/calendar/slots?date={tomorrow}",
        headers=auth_headers,
    )
    assert resp.status_code == 200


def test_health_endpoint(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
