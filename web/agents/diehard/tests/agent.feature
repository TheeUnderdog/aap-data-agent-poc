@agent @diehard
Feature: DieHard agent acceptance
  As a CUA testing the Advance Insights app,
  I need to verify the DieHard agent shows its store-operations identity,
  offers location-focused prompts, and answers operations questions as DieHard.

  Background:
    Given I open my browser to http://localhost:5000
    And I wait for the page to fully load
    And I click the "DieHard" tab in the left sidebar

  @id:diehard-welcome-identity
  Scenario: DieHard welcome and identity are shown
    Then the "DieHard" tab should appear selected/highlighted
    And the active agent label in the header should update to show "DieHard"
    And I should see the agent description "Store Operations"
    And the chat area should show the welcome message "Store performance, operations data — what do you need?"
    And the tab text and accent color should be red (#B6121B)

  @id:diehard-sample-questions-visible
  Scenario: DieHard suggestions show store operations sample questions
    When I click the lightbulb icon button near the input area
    Then the suggestions panel should list sample questions for "DieHard"
    And I should see "What are our top 5 stores by revenue?"
    And I should see "Show me store performance by region"
    And I should see "Which locations have the highest return rates?"
    And each listed suggestion should look clickable/selectable

  @id:diehard-sample-question-clickable
  Scenario: Clicking a DieHard sample question populates the input
    Given I open the suggestions panel for "DieHard"
    When I click "What's the average transaction value by store?"
    Then the chat input field should contain "What's the average transaction value by store?"
    And the input should still be ready to send
    And the populated question should clearly be about stores, regions, sales, or operations

  @id:diehard-chat-response-relevant
  Scenario: DieHard answers a store performance question
    When I send "What are our top 5 stores by revenue?"
    And I wait for the response (up to 45 seconds)
    Then the response should come from the DieHard Fabric agent
    And the response should mention stores, regions, revenue, transaction value, returns, or operational performance
    And the response should feel relevant to store operations rather than customer service, loyalty administration, marketing, or merchandising

  @id:diehard-mystery-prompt
  Scenario: DieHard mystery prompt generates a store-operations question
    When I click the dice icon button near the input area
    Then within 10 seconds a question should appear in the input field
    And the generated question should be relevant to a district manager or store operations lead
    And the generated question should mention ideas like return rate outliers, regional revenue variance, channel mix, weekend vs. weekday patterns, store ramp-up, or underperforming locations
