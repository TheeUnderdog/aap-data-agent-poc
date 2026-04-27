@core @chat
Feature: Chat Flow — Send and Receive Messages
  As a CUA testing the Advance Insights app,
  I need to verify that I can send a question to an agent
  and receive a meaningful response in the chat area.

  Background:
    Given I open my browser to http://localhost:5000
    And I wait for the page to fully load

  @id:03-chat-flow-send-gearup
  Scenario: Send a simple question to GearUp (Loyalty agent)
    Given I click the "GearUp" tab
    When I click into the text input at the bottom
    And I type "How many active loyalty members do we have?"
    And I click the Send button (arrow icon to the right of input)
    Then my message should appear as a user bubble in the chat area
    And a loading/thinking indicator should appear below my message
    And within 30 seconds, an agent response bubble should appear
    And the response should contain text (not be empty)
    And the response should mention numbers or member-related information

  @id:03-chat-flow-enter-key
  Scenario: Send a question using Enter key
    Given I am on the "Pit Crew" tab
    When I click into the text input
    And I type "What are the top complaint categories?"
    And I press the Enter key (not Shift+Enter)
    Then my message should be sent (input clears)
    And a user bubble with my question appears in the chat
    And within 30 seconds, an agent response appears

  @id:03-chat-flow-input-clears
  Scenario: Input clears after sending
    Given I am on any agent tab
    When I type "test question" in the input and send it
    Then the input field should be empty after sending
    And the input should remain focused and ready for another question

  @id:03-chat-flow-empty-guard
  Scenario: Cannot send empty message
    Given I am on any agent tab
    And the input field is empty
    When I click the Send button
    Then no message should be sent
    And no new bubbles should appear in the chat area

  @id:03-chat-flow-formatted-response
  Scenario: Agent response includes formatted content
    Given I am on the "PartsPro" tab
    When I send "Show me the top 10 selling products this month"
    And I wait for the response (up to 45 seconds — data queries may be slower)
    Then the response should appear with readable formatting
    # Responses may include tables, bullet lists, bold text, or numbered items
    And the response should not be raw markdown (it should be rendered HTML)

  @id:03-chat-flow-conversation-thread
  Scenario: Multiple messages create a conversation thread
    Given I am on the "GearUp" tab
    When I send "How many members are in Gold tier?"
    And I wait for the response
    And then I send "What about Platinum tier?"
    And I wait for the response
    Then I should see 4 bubbles total: user, agent, user, agent
    And they should be in chronological order (top to bottom)
    And the second response should understand the context of the first question

  @id:03-chat-flow-new-chat-clears
  Scenario: New Chat button clears conversation
    Given I am on any tab with an existing conversation (at least one exchange)
    When I click the New Chat button (+ icon in the header)
    Then the chat area should be cleared
    And only the welcome message should remain
    And the input should be empty and ready

  @id:03-chat-flow-long-response
  Scenario: Long response renders without breaking layout
    Given I am on the "Crew Chief" tab
    When I send "Give me a cross-department summary of Q4 performance"
    And I wait for the response (up to 60 seconds — Crew Chief routes to multiple agents)
    Then the response should render fully without overflowing the chat area
    And I should be able to scroll through the response if it's long
    And the input bar should remain visible at the bottom
