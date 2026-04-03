Feature: Appointment Scheduling
  As an authenticated provider
  I want to schedule and manage appointments
  So that patients receive timely care

  Background:
    Given I am authenticated as "appt.provider@medaea.com" with password "Appt123!"
    And a patient exists for scheduling tests

  Scenario: List my appointments
    When I GET "/api/v1/appointments/me"
    Then the response status code should be 200
    And the response body should be a JSON array

  Scenario: Create a valid appointment
    When I POST to "/api/v1/appointments" with:
      | appointment_date | appointment_time | duration_minutes | visit_type   |
      | {tomorrow}       | 09:00            | 30               | office_visit |
    Then the response status code should be 201
    And the response body should include "id"

  Scenario: Create appointment with missing required fields
    When I POST to "/api/v1/appointments" with an empty body
    Then the response status code should be 422

  Scenario: View calendar events for a date range
    When I GET "/api/v1/calendar/events?start={today}&end={next_week}"
    Then the response status code should be 200

  Scenario: Get available booking slots for a date
    When I GET "/api/v1/calendar/slots?date={tomorrow}"
    Then the response status code should be 200

  Scenario: Create a PTO request
    When I POST to "/api/v1/calendar/pto" with:
      | start_date    | end_date      | reason   | pto_type |
      | {in_10_days}  | {in_12_days}  | Vacation | vacation |
    Then the response status code should be 201
    And the response body should include "id"
