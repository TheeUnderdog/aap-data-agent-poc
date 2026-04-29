@agent @crew-chief
Feature: Crew Chief agent acceptance
  As a CUA testing the Advance Insights app,
  I need to verify the Crew Chief agent shows its executive orchestrator identity,
  presents cross-functional prompts, and routes questions to the right specialists.

  Background:
    Given I open my browser to http://localhost:5000
    And I wait for the page to fully load
    And I click the "Crew Chief" tab in the left sidebar

  @id:crew-chief-welcome-identity
  Scenario: Crew Chief welcome and identity are shown
    Then the "Crew Chief" tab should appear selected/highlighted
    And the active agent label in the header should update to show "Crew Chief"
    And I should see the agent description "Executive orchestrator"
    And the chat area should show the welcome message "I coordinate the full team. Ask me anything — I'll get the right agent on it."
    And the tab text and accent color should be black (#1E1E1E)

  @id:crew-chief-sample-questions-visible
  Scenario: Crew Chief suggestions show cross-functional sample questions
    When I click the lightbulb icon button near the input area
    Then the suggestions panel should list sample questions for "Crew Chief"
    And I should see "How are our top-tier loyalty members responding to the holiday promo?"
    And I should see "Which stores have the highest revenue and most reward redemptions?"
    And I should see "Compare campaign engagement rates across our top 10 stores"
    And each listed suggestion should look clickable/selectable

  @id:crew-chief-sample-question-clickable
  Scenario: Clicking a Crew Chief sample question populates the input
    Given I open the suggestions panel for "Crew Chief"
    When I click "Show me a cross-department summary of Q4 performance"
    Then the chat input field should contain "Show me a cross-department summary of Q4 performance"
    And the input should still be ready to send
    And the populated question should clearly be a cross-functional executive ask

  @id:crew-chief-routing-fanout
  Scenario: Crew Chief routes a cross-functional question to specialist agents
    When I send "How are our top-tier loyalty members responding to the holiday promo?"
    And I wait for the response (up to 60 seconds — Crew Chief may fan out to multiple agents)
    Then the response should come from the Crew Chief experience, not a single specialist tab
    And the answer should reference at least two specialist domains such as loyalty, marketing, store operations, merchandising, or customer service
    And the result should feel synthesized or summarized for an executive audience
    And if routed sub-agent activity is shown, it should reference the correct contributing agents

  @id:crew-chief-mystery-prompt
  Scenario: Crew Chief mystery prompt generates a cross-functional executive question
    When I click the dice icon button near the input area
    Then within 10 seconds a question should appear in the input field
    And the generated question should be relevant to an executive orchestrator
    And the generated question should span at least two specialist domains
    And it should not be limited to only one agent's subject area
