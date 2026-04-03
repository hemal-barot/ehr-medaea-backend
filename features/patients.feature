Feature: Patient Management
  As an authenticated provider
  I want to manage patient records
  So that I can deliver coordinated care

  Background:
    Given I am authenticated as "patient.provider@medaea.com" with password "Provider123!"

  Scenario: List patients returns an array
    When I GET "/api/v1/patients"
    Then the response status code should be 200
    And the response body should be a JSON array

  Scenario: Create a new patient record
    When I POST to "/api/v1/patients" with patient details:
      | first_name | last_name | date_of_birth | gender | email                   |
      | Maria      | Garcia    | 1978-03-22    | female | maria.garcia@patient.com |
    Then the response status code should be 201
    And the response body should include "id"
    And the response body should include "first_name" equal to "Maria"

  Scenario: Retrieve a specific patient by ID
    Given a patient exists with first name "John" and last name "Patient"
    When I GET "/api/v1/patients/{patient_id}"
    Then the response status code should be 200
    And the patient's last name should be "Patient"

  Scenario: Request a non-existent patient returns 404
    When I GET "/api/v1/patients/99999999"
    Then the response status code should be 404

  Scenario: View patient allergies
    Given a patient exists with first name "Allergy" and last name "Test"
    When I GET "/api/v1/patients/{patient_id}/allergies"
    Then the response status code should be 200
    And the response body should be a JSON array

  Scenario: View patient medications
    Given a patient exists with first name "Med" and last name "Check"
    When I GET "/api/v1/patients/{patient_id}/medications"
    Then the response status code should be 200
