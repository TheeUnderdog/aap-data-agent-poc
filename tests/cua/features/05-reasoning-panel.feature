@secondary @reasoning
Feature: Reasoning Panel
  As a CUA testing the Advance Insights app,
  I need to verify the reasoning panel slides out,
  displays chain-of-thought steps, groups reasoning
  by question, and responds to agent avatar clicks.

  Background:
    Given I open my browser to http://localhost:5000
    And I wait for the page to fully load

  Scenario: Toggle reasoning panel open via header button
    When I click the reasoning toggle button in the header (brain/info icon)
    Then a panel should slide out from the right side of the screen
    And the panel should have a header or title like "Agent Reasoning"
    And the chat area should resize to make room for the panel

  Scenario: Toggle reasoning panel closed
    Given the reasoning panel is open
    When I click the reasoning toggle button again
    Then the panel should slide closed (hide to the right)
    And the chat area should expand back to full width

  Scenario: Reasoning steps appear after asking a question
    Given I am on the "GearUp" tab
    And the reasoning panel is open
    When I send "How many Gold tier members do we have?"
    And I wait for the response (up to 30 seconds)
    Then the reasoning panel should show a new group/section for this question
    And within the group I should see one or more reasoning steps
    And each step should show text describing what the agent did
    And each step should show a duration (e.g., "2.3s" or similar timing)

  Scenario: Reasoning groups are collapsible
    Given I have asked at least 2 questions and received responses
    And the reasoning panel is open
    Then I should see 2 reasoning groups (one per question)
    When I click the header of the first group
    Then it should collapse (hide its steps)
    When I click it again
    Then it should expand (show its steps again)

  Scenario: Token usage is displayed
    Given I have asked a question and received a response
    And the reasoning panel is open
    Then somewhere in the reasoning panel I should see token counts
    # Token info shows prompt tokens, completion tokens, and total
    And the numbers should be reasonable (hundreds to thousands)

  Scenario: Click agent avatar to open reasoning for that interaction
    Given I have asked a question and received a response
    And the reasoning panel is CLOSED
    When I click the agent avatar/icon to the left of the agent's response bubble
    Then the reasoning panel should slide open
    And it should scroll to (or highlight) the reasoning group for that specific response
    # This connects the chat bubble to its reasoning entry

  Scenario: Methodology extraction appears in reasoning
    # When an agent says "How I got these numbers:" or similar,
    # that content moves from the chat bubble to the reasoning panel
    Given I am on the "Ignition" tab
    And the reasoning panel is open
    When I send "What campaigns had the highest response rates last quarter?"
    And I wait for the response (up to 45 seconds)
    Then if the response originally contained methodology/reasoning text
    Then that methodology should appear in the reasoning panel (not in the chat bubble)
    # The chat bubble shows the clean answer; reasoning panel shows the "show your work"

  Scenario: Multiple agents show separate reasoning when Crew Chief routes
    Given I am on the "Crew Chief" tab
    And the reasoning panel is open
    When I send "Compare loyalty program performance with marketing campaign results"
    And I wait for the full response (up to 60 seconds — multi-agent query)
    Then the reasoning panel should show groups from multiple agents
    And each group should identify which agent produced it (by name or color)
