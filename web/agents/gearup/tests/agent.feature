@agent @gearup
Feature: GearUp agent acceptance
  As a CUA testing the Advance Insights app,
  I need to verify the GearUp agent shows its loyalty-program identity,
  offers rewards-focused prompts, and answers member questions as GearUp.

  Background:
    Given I open my browser to http://localhost:5000
    And I wait for the page to fully load
    And I click the "GearUp" tab in the left sidebar

  @id:gearup-welcome-identity
  Scenario: GearUp welcome and identity are shown
    Then the "GearUp" tab should appear selected/highlighted
    And the active agent label in the header should update to show "GearUp"
    And I should see the agent description "Loyalty Program Manager"
    And the chat area should show the welcome message "Let's check in on the loyalty program. What do you want to know?"
    And the tab should use a gold/yellow accent (#FFCC00) with deep gold text (#B38600)

  @id:gearup-sample-questions-visible
  Scenario: GearUp suggestions show loyalty sample questions
    When I click the lightbulb icon button near the input area
    Then the suggestions panel should list sample questions for "GearUp"
    And I should see "How many active loyalty members do we have?"
    And I should see "What's the breakdown of members by tier?"
    And I should see "Which rewards are most popular among Gold tier members?"
    And each listed suggestion should look clickable/selectable

  @id:gearup-sample-question-clickable
  Scenario: Clicking a GearUp sample question populates the input
    Given I open the suggestions panel for "GearUp"
    When I click "How many points were redeemed last quarter?"
    Then the chat input field should contain "How many points were redeemed last quarter?"
    And the input should still be ready to send
    And the populated question should clearly be about members, tiers, points, or rewards

  @id:gearup-chat-response-relevant
  Scenario: GearUp answers a loyalty member question
    When I send "How many active loyalty members do we have?"
    And I wait for the response (up to 45 seconds)
    Then the response should come from the GearUp Fabric agent
    And the response should mention members, tiers, points, rewards, or enrollment information
    And the response should feel relevant to loyalty program management rather than customer service, marketing, merchandising, or store operations

  @id:gearup-mystery-prompt
  Scenario: GearUp mystery prompt generates a loyalty-relevant question
    When I click the dice icon button near the input area
    Then within 10 seconds a question should appear in the input field
    And the generated question should be relevant to a loyalty program manager
    And the generated question should mention ideas like tier migration, churn risk, points liability, enrollment cohorts, engagement drop-offs, or reward redemptions
