"""
Behave environment hooks for Medaea EHR BDD tests.
Sets a default base URL (overridable via MEDAEA_API_URL env var).
"""
import os


def before_all(context):
    context.base_url = os.getenv("MEDAEA_API_URL", "http://localhost:8000")
    context.auth_headers = {}
    context.patient_id = None
    context.token = None
