@secondary @ui
Feature: Suggestions Panel
  As a CUA testing the Advance Insights app,
  I need to verify the suggestions lightbulb panel opens,
  displays sample questions for the active agent, and
  populates the input when a suggestion is clicked.

  Background:
    Given I open my browser to http://localhost:5000
    And I wait for the page to fully load

  @id:04-suggestions-open-panel
  Scenario: Open suggestions panel via lightbulb button
    Given I am on the "Crew Chief" tab
    When I click the lightbulb icon button near the input area
    Then a suggestions panel should slide out or appear
    And it should contain a list of sample questions
    And the questions should be relevant to the Crew Chief agent

  @id:04-suggestions-click-populates
  Scenario: Click a suggestion to populate input
    Given I am on the "GearUp" tab
    And I open the suggestions panel (click lightbulb)
    When I click on one of the listed sample questions
    Then that question text should appear in the chat input field
    And the suggestions panel should close (or remain open — either is fine)
    And the input should be ready to send (I can press Enter or click Send)

  @id:04-suggestions-per-agent
  Scenario: Suggestions change per agent
    Given I am on the "Ignition" tab
    And I open the suggestions panel
    Then the sample questions should be marketing/campaign related
    When I close the panel (if needed) and switch to the "DieHard" tab
    And I open the suggestions panel again
    Then the sample questions should be store/operations related
    And they should be different from what Ignition showed

  @id:04-suggestions-close-panel
  Scenario: Close suggestions panel
    Given the suggestions panel is open
    When I click the lightbulb button again (or click outside the panel)
    Then the suggestions panel should close/hide
    And the main chat area should be fully visible again

  @id:04-suggestions-dice-button
  Scenario: Mystery Question dice button
    # The dice button generates a creative AI-powered question
    Given I am on any agent tab
    When I look near the input area for a dice icon button
    And I click the dice button
    Then the dice should show a spin animation
    And within 10 seconds a question should appear in the input field
    And the dice should stop spinning and show random pips (dots)
    # The generated question is from the agent's mystery prompt — should be creative/fun
