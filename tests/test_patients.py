"""
Tests for patient CRUD endpoints:
  GET    /api/v1/patients
  POST   /api/v1/patients
  GET    /api/v1/patients/{id}
  PUT    /api/v1/patients/{id}
  DELETE /api/v1/patients/{id}
"""
import pytest


PATIENT_PAYLOAD = {
    "first_name": "Jane",
    "last_name": "Doe",
    "date_of_birth": "1985-06-15",
    "gender": "female",
    "email": "janedoe@patient-test.com",
    "phone": "555-0100",
    "address": "123 Main St",
    "city": "Boston",
    "state": "MA",
    "zip_code": "02101",
}


def test_list_patients_requires_auth(client):
    resp = client.get("/api/v1/patients")
    assert resp.status_code == 401


def test_list_patients(client, auth_headers):
    resp = client.get("/api/v1/patients", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_create_patient(client, auth_headers):
    resp = client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=auth_headers)
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert data["first_name"] == "Jane"
    assert data["last_name"] == "Doe"
    assert "id" in data


def test_create_patient_missing_required(client, auth_headers):
    resp = client.post("/api/v1/patients", json={"first_name": "Only"}, headers=auth_headers)
    assert resp.status_code == 422


def test_get_patient_by_id(client, auth_headers):
    create_resp = client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=auth_headers)
    patient_id = create_resp.json()["id"]

    resp = client.get(f"/api/v1/patients/{patient_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == patient_id


def test_get_patient_not_found(client, auth_headers):
    resp = client.get("/api/v1/patients/99999999", headers=auth_headers)
    assert resp.status_code == 404


def test_update_patient(client, auth_headers):
    create_resp = client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=auth_headers)
    patient_id = create_resp.json()["id"]

    resp = client.put(
        f"/api/v1/patients/{patient_id}",
        json={**PATIENT_PAYLOAD, "city": "Cambridge"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["city"] == "Cambridge"


def test_patient_allergies_endpoint(client, auth_headers):
    create_resp = client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=auth_headers)
    patient_id = create_resp.json()["id"]

    resp = client.get(f"/api/v1/patients/{patient_id}/allergies", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_patient_medications_endpoint(client, auth_headers):
    create_resp = client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=auth_headers)
    patient_id = create_resp.json()["id"]

    resp = client.get(f"/api/v1/patients/{patient_id}/medications", headers=auth_headers)
    assert resp.status_code == 200
