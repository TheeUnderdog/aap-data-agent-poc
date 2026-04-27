"""
UI test fixtures — browser setup, authenticated page, helpers.

CUA INSTRUCTIONS:
    These fixtures handle browser launch and app navigation.
    The app uses proxy mode so there is NO login gate to click through.
    The page fixture navigates to the app and waits for it to be interactive.
"""
import pytest
from playwright.sync_api import Page, expect


@pytest.fixture
def app_page(page: Page, base_url: str) -> Page:
    """
    Navigate to the app and wait until it's fully loaded and interactive.

    WHAT THIS DOES:
    1. Opens the browser to the app URL
    2. Waits for the main app container to appear (login is bypassed in proxy mode)
    3. Returns the page ready for interaction

    IF THIS FAILS:
    - The server is not running (start with: cd web && python server.py)
    - Or the server failed to authenticate (run: az login first)
    """
    page.goto(base_url)
    page.wait_for_load_state("networkidle")

    # In proxy mode, the app auto-shows (no login click needed).
    # Wait for the main app container to be visible.
    app_container = page.locator("#app")
    expect(app_container).to_be_visible(timeout=10_000)

    return page


# ── Helper: Agent tab names (matches config.js agentOrder) ────────────────

AGENT_TABS = [
    {"key": "crew-chief", "name": "Crew Chief", "description": "Executive orchestrator"},
    {"key": "pit-crew", "name": "Pit Crew", "description": "Customer Service & Support"},
    {"key": "gearup", "name": "GearUp", "description": "Loyalty Program Manager"},
    {"key": "ignition", "name": "Ignition", "description": "Marketing & Promotions"},
    {"key": "partspro", "name": "PartsPro", "description": "Merchandising & Categories"},
    {"key": "diehard", "name": "DieHard", "description": "Store Operations"},
]
