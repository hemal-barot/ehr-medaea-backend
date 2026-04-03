"""
Tests for authentication endpoints:
  POST /api/v1/auth/signup
  POST /api/v1/auth/login
  GET  /api/v1/users/me
  POST /api/v1/auth/forgot-password
"""
import pytest


def test_signup_success(client):
    resp = client.post("/api/v1/auth/signup", json={
        "email": "signup.success@medaea-test.com",
        "password": "Signup123!",
        "first_name": "Alice",
        "last_name": "Smith",
        "role": "physician",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_signup_duplicate_email(client):
    payload = {
        "email": "dup@medaea-test.com",
        "password": "Dup123!",
        "first_name": "Bob",
        "last_name": "Dup",
        "role": "nurse",
    }
    client.post("/api/v1/auth/signup", json=payload)
    resp = client.post("/api/v1/auth/signup", json=payload)
    assert resp.status_code in (400, 409)


def test_signup_weak_password(client):
    resp = client.post("/api/v1/auth/signup", json={
        "email": "weak@medaea-test.com",
        "password": "123",
        "first_name": "Weak",
        "last_name": "Pass",
        "role": "physician",
    })
    assert resp.status_code == 422


def test_login_success(client, provider_payload, auth_headers):
    assert "Authorization" in auth_headers
    assert auth_headers["Authorization"].startswith("Bearer ")


def test_login_wrong_password(client, provider_payload):
    client.post("/api/v1/auth/signup", json=provider_payload)
    resp = client.post("/api/v1/auth/login", data={
        "username": provider_payload["email"],
        "password": "WrongPassword!",
    })
    assert resp.status_code in (400, 401)


def test_login_nonexistent_user(client):
    resp = client.post("/api/v1/auth/login", data={
        "username": "nobody@medaea-test.com",
        "password": "SomePass123!",
    })
    assert resp.status_code in (400, 401, 404)


def test_get_me_authenticated(client, auth_headers):
    resp = client.get("/api/v1/users/me", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "email" in data
    assert "id" in data


def test_get_me_unauthenticated(client):
    resp = client.get("/api/v1/users/me")
    assert resp.status_code == 401


def test_get_me_invalid_token(client):
    resp = client.get("/api/v1/users/me", headers={"Authorization": "Bearer invalid.token.here"})
    assert resp.status_code == 401
