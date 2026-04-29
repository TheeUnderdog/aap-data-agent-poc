@agent @partspro
Feature: PartsPro agent acceptance
  As a CUA testing the Advance Insights app,
  I need to verify the PartsPro agent shows its merchandising identity,
  offers product-focused prompts, and answers category questions as PartsPro.

  Background:
    Given I open my browser to http://localhost:5000
    And I wait for the page to fully load
    And I click the "PartsPro" tab in the left sidebar

  @id:partspro-welcome-identity
  Scenario: PartsPro welcome and identity are shown
    Then the "PartsPro" tab should appear selected/highlighted
    And the active agent label in the header should update to show "PartsPro"
    And I should see the agent description "Merchandising & Categories"
    And the chat area should show the welcome message "Products, categories, inventory trends — ask away."
    And the tab text and accent color should be green (#2D8A4E)

  @id:partspro-sample-questions-visible
  Scenario: PartsPro suggestions show merchandising sample questions
    When I click the lightbulb icon button near the input area
    Then the suggestions panel should list sample questions for "PartsPro"
    And I should see "What are our top 10 selling products this month?"
    And I should see "Show me revenue by product category"
    And I should see "What's the average basket size by product category?"
    And each listed suggestion should look clickable/selectable

  @id:partspro-sample-question-clickable
  Scenario: Clicking a PartsPro sample question populates the input
    Given I open the suggestions panel for "PartsPro"
    When I click "Which brands have the highest average transaction value?"
    Then the chat input field should contain "Which brands have the highest average transaction value?"
    And the input should still be ready to send
    And the populated question should clearly be about products, brands, categories, or merchandising trends

  @id:partspro-chat-response-relevant
  Scenario: PartsPro answers a product performance question
    When I send "What are our top 10 selling products this month?"
    And I wait for the response (up to 45 seconds)
    Then the response should come from the PartsPro Fabric agent
    And the response should mention products, categories, brands, inventory trends, or basket metrics
    And the response should feel relevant to merchandising rather than customer service, loyalty administration, marketing, or store operations

  @id:partspro-mystery-prompt
  Scenario: PartsPro mystery prompt generates a merchandising-relevant question
    When I click the dice icon button near the input area
    Then within 10 seconds a question should appear in the input field
    And the generated question should be relevant to a category manager
    And the generated question should mention ideas like return rates by category, brand concentration, SKU outliers, cross-sell affinity, seasonal mix shifts, or inventory velocity
