"""
Root conftest.py — shared fixtures for all test layers.

CUA INSTRUCTIONS:
    This file provides authentication and configuration fixtures.
    The app runs at http://localhost:5000 in proxy mode (server.py handles auth).
    No manual login is needed — the server authenticates via Azure CLI credential.
"""
import pytest


@pytest.fixture(scope="session")
def app_url(request):
    """Base URL of the running application. Override with --base-url flag."""
    return request.config.getoption("--base-url", default="http://localhost:5000")
