"""
Behave step definitions for authentication scenarios.
"""
import json
import requests
from behave import given, when, then


def api_url(context, path):
    base = getattr(context, "base_url", "http://localhost:8000")
    return f"{base}{path}"


@given('the API is running at "{url}"')
def step_set_base_url(context, url):
    context.base_url = url


@given('I am a new provider with email "{email}"')
def step_new_provider(context, email):
    context.signup_email = email


@when('I submit a signup request with password "{password}" and role "{role}"')
def step_submit_signup(context, password, role):
    context.response = requests.post(
        api_url(context, "/api/v1/auth/signup"),
        json={
            "email": context.signup_email,
            "password": password,
            "first_name": "BDD",
            "last_name": "Tester",
            "role": role,
        },
    )


@given('a provider already exists with email "{email}"')
def step_provider_exists(context, email):
    context.signup_email = email
    requests.post(
        api_url(context, "/api/v1/auth/signup"),
        json={
            "email": email,
            "password": "Existing123!",
            "first_name": "Already",
            "last_name": "Exists",
            "role": "physician",
        },
    )


@when('I submit a signup request with that email and password "{password}"')
def step_signup_duplicate(context, password):
    context.response = requests.post(
        api_url(context, "/api/v1/auth/signup"),
        json={
            "email": context.signup_email,
            "password": password,
            "first_name": "Dup",
            "last_name": "User",
            "role": "nurse",
        },
    )


@given('a provider exists with email "{email}" and password "{password}"')
def step_create_provider(context, email, password):
    context.login_email = email
    context.login_password = password
    requests.post(
        api_url(context, "/api/v1/auth/signup"),
        json={
            "email": email,
            "password": password,
            "first_name": "Login",
            "last_name": "User",
            "role": "physician",
        },
    )


@when("I submit a login request with those credentials")
def step_login_correct(context):
    context.response = requests.post(
        api_url(context, "/api/v1/auth/login"),
        data={"username": context.login_email, "password": context.login_password},
    )


@when('I submit a login request with password "{password}"')
def step_login_wrong(context, password):
    context.response = requests.post(
        api_url(context, "/api/v1/auth/login"),
        data={"username": context.login_email, "password": password},
    )


@when('I request "{path}" without authentication')
def step_request_no_auth(context, path):
    context.response = requests.get(api_url(context, path))


@given('I am authenticated as "{email}" with password "{password}"')
def step_authenticate(context, email, password):
    requests.post(
        api_url(context, "/api/v1/auth/signup"),
        json={
            "email": email,
            "password": password,
            "first_name": "Auth",
            "last_name": "User",
            "role": "physician",
        },
    )
    resp = requests.post(
        api_url(context, "/api/v1/auth/login"),
        data={"username": email, "password": password},
    )
    context.token = resp.json().get("access_token", "")
    context.auth_headers = {"Authorization": f"Bearer {context.token}"}


@when('I request "{path}" with my token')
def step_request_with_token(context, path):
    context.response = requests.get(
        api_url(context, path),
        headers=context.auth_headers,
    )


@then("the response status code should be {code:d}")
def step_check_status(context, code):
    actual = context.response.status_code
    assert actual == code, f"Expected {code}, got {actual}. Body: {context.response.text}"


@then('the response should contain an "{field}"')
def step_check_field(context, field):
    data = context.response.json()
    assert field in data, f"Field '{field}' not in response: {data}"


@then('the token type should be "{token_type}"')
def step_check_token_type(context, token_type):
    data = context.response.json()
    assert data.get("token_type") == token_type


@then("the response body should include my email")
def step_check_email(context):
    data = context.response.json()
    assert "email" in data
