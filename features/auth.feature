Feature: User Authentication
  As a healthcare provider
  I want to securely authenticate with the Medaea EHR system
  So that I can access patient records and clinical tools

  Background:
    Given the API is running at "http://localhost:8000"

  Scenario: Successful provider signup
    Given I am a new provider with email "bdd.provider@medaea.com"
    When I submit a signup request with password "BddTest123!" and role "physician"
    Then the response status code should be 200
    And the response should contain an "access_token"
    And the token type should be "bearer"

  Scenario: Duplicate email registration is rejected
    Given a provider already exists with email "existing@medaea.com"
    When I submit a signup request with that email and password "Duplicate123!"
    Then the response status code should be 409

  Scenario: Successful login returns JWT
    Given a provider exists with email "login.bdd@medaea.com" and password "Login123!"
    When I submit a login request with those credentials
    Then the response status code should be 200
    And the response should contain an "access_token"

  Scenario: Login with wrong password is rejected
    Given a provider exists with email "wrongpass@medaea.com" and password "CorrectPass123!"
    When I submit a login request with password "WrongPassword!"
    Then the response status code should be 401

  Scenario: Accessing protected endpoint without token is rejected
    When I request "/api/v1/users/me" without authentication
    Then the response status code should be 401

  Scenario: Accessing protected endpoint with valid token succeeds
    Given I am authenticated as "authed@medaea.com" with password "Auth123!"
    When I request "/api/v1/users/me" with my token
    Then the response status code should be 200
    And the response body should include my email
