@secondary @ui
Feature: Copy Button on Agent Responses
  As a CUA testing the Advance Insights app,
  I need to verify that each agent response has a copy button
  that copies the response content to the clipboard.

  Background:
    Given I open my browser to http://localhost:5000
    And I wait for the page to fully load

  Scenario: Copy button is visible on agent response
    Given I am on the "GearUp" tab
    When I send "How many total members are in the program?"
    And I wait for the agent to respond
    Then the agent response bubble should have a copy button
    # The copy button is typically a clipboard/copy icon that appears
    # on hover or is always visible near the agent message

  Scenario: Click copy button copies response text
    Given there is an agent response with a copy button visible
    When I click the copy button on the agent response
    Then I should see a brief confirmation (tooltip change, checkmark, or "Copied!" text)
    # The response content should now be on the clipboard
    # To verify: click into the input field and paste (Ctrl+V)
    When I click into the chat input and press Ctrl+V (or Cmd+V)
    Then the pasted content should match the agent's response text

  Scenario: Copy button works on responses with tables
    Given I am on the "PartsPro" tab
    When I send "Show me top 5 product categories by revenue"
    And I wait for the response (should include a table)
    And I click the copy button on that response
    Then the copied content should include the table data
    # When pasted, it should be readable text (not HTML tags)

  Scenario: Each response has its own copy button
    Given I am on any agent tab
    When I send two questions and receive two responses
    Then each response bubble should have its own separate copy button
    And clicking copy on the second response should only copy that response
    # Not the entire conversation

  Scenario: Copy button does not copy user messages
    Given there is a conversation with user and agent messages
    Then only the agent response bubbles should have copy buttons
    And user message bubbles should NOT have a copy button
