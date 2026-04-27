"""
TEST SUITE: Page Load & Basic Rendering
========================================
GOAL: Verify the app loads successfully and all major UI elements render.

CUA INSTRUCTIONS:
    Run: pytest tests/ui/test_page_load.py -v --headed
    WHAT TO LOOK FOR: The app should display a header bar, agent tabs on the left,
    a chat area in the center, and an input bar at the bottom.
    If any test fails, check the screenshot in tests/results/ for visual diagnosis.
"""
import pytest
from playwright.sync_api import Page, expect
from tests.ui.conftest import AGENT_TABS


@pytest.mark.smoke
@pytest.mark.ui
class TestPageLoad:
    """Verify the application loads and renders its core structure."""

    def test_page_title_contains_aap(self, app_page: Page):
        """
        USER STORY: When I navigate to the app, the browser tab shows the app name.

        ACTION: Open the app URL in a browser.
        VERIFY: The page title contains "Advance Insights".
        """
        expect(app_page).to_have_title(r".*Advance Insights.*")

    def test_header_bar_is_visible(self, app_page: Page):
        """
        USER STORY: The top bar shows the AAP branding.

        ACTION: Look at the top of the page.
        VERIFY: You can see "ADVANCE" and "INSIGHTS" in the header.
        """
        # VERIFY: Header bar exists
        header = app_page.locator("header.top-bar")
        expect(header).to_be_visible()

        # VERIFY: Brand wordmark is present
        expect(app_page.get_by_text("ADVANCE")).to_be_visible()
        expect(app_page.get_by_text("INSIGHTS")).to_be_visible()

    def test_aap_logo_is_visible(self, app_page: Page):
        """
        USER STORY: The AAP logo appears in the header.

        ACTION: Look at the top-left corner.
        VERIFY: An image with alt text "AAP" is displayed.
        """
        logo = app_page.get_by_alt_text("AAP")
        expect(logo).to_be_visible()

    def test_agent_tabs_are_rendered(self, app_page: Page):
        """
        USER STORY: All 6 agent tabs appear in the navigation strip.

        ACTION: Look at the left side tab strip (or top on mobile).
        VERIFY: You see tabs for Crew Chief, Pit Crew, GearUp, Ignition,
                PartsPro, and DieHard.
        """
        for agent in AGENT_TABS:
            # Each tab displays the agent name as text
            tab = app_page.get_by_text(agent["name"], exact=True).first
            expect(tab).to_be_visible()

    def test_chat_input_is_visible(self, app_page: Page):
        """
        USER STORY: There is a text input at the bottom where I can type questions.

        ACTION: Look at the bottom of the page.
        VERIFY: A textarea with placeholder "Ask a question..." is visible and enabled.
        """
        input_field = app_page.get_by_placeholder("Ask a question...")
        expect(input_field).to_be_visible()
        expect(input_field).to_be_enabled()

    def test_send_button_is_visible(self, app_page: Page):
        """
        USER STORY: There is a send button next to the input.

        ACTION: Look at the right side of the input bar.
        VERIFY: A button with title "Send message" is visible.
        """
        send_btn = app_page.get_by_title("Send message")
        expect(send_btn).to_be_visible()

    def test_user_name_is_displayed(self, app_page: Page):
        """
        USER STORY: My identity shows in the top-right corner.

        ACTION: Look at the top-right area of the header.
        VERIFY: A text element shows "Connected" (proxy mode) or the user's name.
        """
        user_display = app_page.locator("#user-name")
        expect(user_display).to_be_visible()
        # In proxy mode, shows "Connected"
        expect(user_display).not_to_be_empty()

    def test_sign_out_button_exists(self, app_page: Page):
        """
        USER STORY: I can sign out of the application.

        ACTION: Look at the top-right area.
        VERIFY: A "Sign out" button is present.
        """
        signout = app_page.get_by_text("Sign out")
        expect(signout).to_be_visible()

    def test_new_chat_button_exists(self, app_page: Page):
        """
        USER STORY: I can start a new conversation.

        ACTION: Look at the top-right area of the header.
        VERIFY: A button with title "New conversation" is present.
        """
        new_chat = app_page.get_by_title("New conversation")
        expect(new_chat).to_be_visible()

    def test_reasoning_toggle_exists(self, app_page: Page):
        """
        USER STORY: I can toggle the agent reasoning panel.

        ACTION: Look at the top-right area of the header.
        VERIFY: A button with title "Show reasoning" is present.
        """
        reasoning_btn = app_page.get_by_title("Show reasoning")
        expect(reasoning_btn).to_be_visible()

    def test_suggestions_button_exists(self, app_page: Page):
        """
        USER STORY: I can see suggested questions for the current agent.

        ACTION: Look at the bottom input area.
        VERIFY: A button with title "Suggestions" is present.
        """
        suggestions_btn = app_page.get_by_title("Suggestions")
        expect(suggestions_btn).to_be_visible()
