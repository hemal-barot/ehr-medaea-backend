"""
Tests for advanced scheduling endpoints:
  GET/POST /api/v1/calendar/pto
  GET/POST /api/v1/calendar/availability-rules
  GET/POST /api/v1/calendar/rooms
"""
import pytest
from datetime import date, timedelta


def test_list_pto_requests(client, auth_headers):
    resp = client.get("/api/v1/calendar/pto", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_create_pto_request(client, auth_headers):
    start = (date.today() + timedelta(days=10)).isoformat()
    end = (date.today() + timedelta(days=12)).isoformat()

    resp = client.post("/api/v1/calendar/pto", json={
        "start_date": start,
        "end_date": end,
        "reason": "Vacation",
        "pto_type": "vacation",
    }, headers=auth_headers)
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert "id" in data


def test_list_availability_rules(client, auth_headers):
    resp = client.get("/api/v1/calendar/availability-rules", headers=auth_headers)
    assert resp.status_code == 200


def test_create_availability_rule(client, auth_headers):
    resp = client.post("/api/v1/calendar/availability-rules", json={
        "day_of_week": 1,
        "start_time": "08:00",
        "end_time": "17:00",
        "is_available": True,
    }, headers=auth_headers)
    assert resp.status_code in (200, 201)


def test_list_rooms(client, auth_headers):
    resp = client.get("/api/v1/calendar/rooms", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_create_room(client, auth_headers):
    resp = client.post("/api/v1/calendar/rooms", json={
        "name": "Exam Room A",
        "room_type": "exam",
        "capacity": 2,
        "is_active": True,
    }, headers=auth_headers)
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert data["name"] == "Exam Room A"
