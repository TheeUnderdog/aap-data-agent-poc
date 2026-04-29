@agent @ignition
Feature: Ignition agent acceptance
  As a CUA testing the Advance Insights app,
  I need to verify the Ignition agent shows its marketing identity,
  offers campaign-focused prompts, and answers promotion questions as Ignition.

  Background:
    Given I open my browser to http://localhost:5000
    And I wait for the page to fully load
    And I click the "Ignition" tab in the left sidebar

  @id:ignition-welcome-identity
  Scenario: Ignition welcome and identity are shown
    Then the "Ignition" tab should appear selected/highlighted
    And the active agent label in the header should update to show "Ignition"
    And I should see the agent description "Marketing & Promotions"
    And the chat area should show the welcome message "Campaigns, promotions, engagement — what are we analyzing?"
    And the tab text and accent color should be orange (#E86C00)

  @id:ignition-sample-questions-visible
  Scenario: Ignition suggestions show campaign sample questions
    When I click the lightbulb icon button near the input area
    Then the suggestions panel should list sample questions for "Ignition"
    And I should see "Which campaign had the highest redemption rate this quarter?"
    And I should see "What's the redemption rate by campaign name?"
    And I should see "Which tier responds best to targeted coupon offers?"
    And each listed suggestion should look clickable/selectable

  @id:ignition-sample-question-clickable
  Scenario: Clicking an Ignition sample question populates the input
    Given I open the suggestions panel for "Ignition"
    When I click "What's the ROI on our top 5 campaigns?"
    Then the chat input field should contain "What's the ROI on our top 5 campaigns?"
    And the input should still be ready to send
    And the populated question should clearly be about campaigns, coupons, or promotions

  @id:ignition-chat-response-relevant
  Scenario: Ignition answers a campaign performance question
    When I send "Which campaign had the highest redemption rate this quarter?"
    And I wait for the response (up to 45 seconds)
    Then the response should come from the Ignition Fabric agent
    And the response should mention campaigns, promotions, coupon offers, redemption rates, or engagement information
    And the response should feel relevant to marketing and promotions rather than customer service, loyalty administration, merchandising, or store operations

  @id:ignition-mystery-prompt
  Scenario: Ignition mystery prompt generates a marketing-relevant question
    When I click the dice icon button near the input area
    Then within 10 seconds a question should appear in the input field
    And the generated question should be relevant to a campaign manager
    And the generated question should mention ideas like coupon funnels, campaign comparisons, targeted promo lift, discount effectiveness, or dormant member reactivation
