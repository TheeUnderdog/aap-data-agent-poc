@agent @pit-crew
Feature: Pit Crew agent acceptance
  As a CUA testing the Advance Insights app,
  I need to verify the Pit Crew agent shows its service-and-support identity,
  offers CSR-focused prompts, and answers customer service questions as Pit Crew.

  Background:
    Given I open my browser to http://localhost:5000
    And I wait for the page to fully load
    And I click the "Pit Crew" tab in the left sidebar

  @id:pit-crew-welcome-identity
  Scenario: Pit Crew welcome and identity are shown
    Then the "Pit Crew" tab should appear selected/highlighted
    And the active agent label in the header should update to show "Pit Crew"
    And I should see the agent description "Customer Service & Support"
    And the chat area should show the welcome message "Ready to dig into service data. What can I look up?"
    And the tab text and accent color should be blue (#2B6CB0)

  @id:pit-crew-sample-questions-visible
  Scenario: Pit Crew suggestions show service sample questions
    When I click the lightbulb icon button near the input area
    Then the suggestions panel should list sample questions for "Pit Crew"
    And I should see "How many CSR activities were logged this month?"
    And I should see "What are the most common CSR activity types this quarter?"
    And I should see "Which members have had the most status changes this year?"
    And each listed suggestion should look clickable/selectable

  @id:pit-crew-sample-question-clickable
  Scenario: Clicking a Pit Crew sample question populates the input
    Given I open the suggestions panel for "Pit Crew"
    When I click "Which CSR department handles the most member interactions?"
    Then the chat input field should contain "Which CSR department handles the most member interactions?"
    And the input should still be ready to send
    And the populated question should clearly be about service and support operations

  @id:pit-crew-chat-response-relevant
  Scenario: Pit Crew answers a CSR activity question
    When I send "How many CSR activities were logged this month?"
    And I wait for the response (up to 45 seconds)
    Then the response should come from the Pit Crew Fabric agent
    And the response should mention CSR activity, support operations, or member service information
    And the response should feel relevant to customer service rather than marketing, loyalty, merchandising, or store operations

  @id:pit-crew-mystery-prompt
  Scenario: Pit Crew mystery prompt generates a service-relevant question
    When I click the dice icon button near the input area
    Then within 10 seconds a question should appear in the input field
    And the generated question should be relevant to customer service or support management
    And the generated question should mention ideas like CSR performance, escalations, complaints, or member service experience
