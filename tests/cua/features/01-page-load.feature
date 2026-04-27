@smoke @ui
Feature: Page Load and Basic Rendering
  As a CUA testing the Advance Insights app,
  I need to verify the application loads successfully
  and all major UI elements are present and visible.

  Background:
    Given I open my browser to http://localhost:5000
    And I wait for the page to fully load (network activity stops)
    # NOTE: The app uses proxy mode — no login screen appears.
    # The main app UI should display immediately.

  Scenario: Page title shows the app name
    Then the browser tab title should contain "Advance Insights"

  Scenario: Header bar displays AAP branding
    Then I should see a header bar at the top of the page
    And the header contains the AAP logo (red/black automotive logo on the left)
    And the header shows the text "ADVANCE" in bold
    And the header shows the text "INSIGHTS" next to it
    And the header shows "Rewards & Loyalty Intelligence" as a tagline

  Scenario: All 6 agent tabs are visible in the left sidebar
    Then I should see a vertical tab strip on the left side
    And the following tabs are listed (top to bottom):
      | Tab Name   | Color  |
      | Crew Chief | black  |
      | Pit Crew   | blue   |
      | GearUp     | gold   |
      | Ignition   | orange |
      | PartsPro   | green  |
      | DieHard    | red    |
    And "Crew Chief" is the currently selected tab (highlighted or active state)

  Scenario: Chat input area is ready for typing
    Then I should see a text input area at the bottom of the page
    And the input has placeholder text "Ask a question..."
    And the input is not disabled (I can click into it)
    And there is a send button (arrow icon) to the right of the input

  Scenario: Header action buttons are present
    Then in the top-right area of the header I should see:
      | Button         | How to identify                    |
      | New Chat       | Plus icon (+) button               |
      | Show Reasoning | Brain/info icon button             |
      | Documentation  | Book icon button                   |
    And I should see a user name or "Connected" text
    And I should see a "Sign out" text button

  Scenario: Suggestions button is available
    Then near the input area I should see a lightbulb icon button
    And this button has the label or title "Suggestions"

  Scenario: Welcome message is displayed for default agent
    Then in the chat area I should see a welcome message
    And the welcome message says something like "I coordinate the full team"
    # This is the Crew Chief's welcome message (default active agent)

  Scenario: No error messages or broken elements
    Then I should NOT see any JavaScript error dialogs
    And I should NOT see any "Setup Required" message
    And I should NOT see any broken image icons (missing images)
    And the page should NOT show a login screen (since proxy mode is active)
