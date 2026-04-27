@core @ui
Feature: Agent Tab Navigation
  As a CUA testing the Advance Insights app,
  I need to verify that clicking different agent tabs
  switches the active agent, updates the UI, and shows
  the correct welcome message and visual styling.

  Background:
    Given I open my browser to http://localhost:5000
    And I wait for the page to fully load
    And "Crew Chief" is the currently active tab

  @id:02-agent-tabs-switch-pit-crew
  Scenario: Switch to Pit Crew agent
    When I click the "Pit Crew" tab in the left sidebar
    Then the "Pit Crew" tab should appear selected/highlighted
    And the active agent label in the header should update to show "Pit Crew"
    And the chat area should show a welcome message containing "Ready to dig into service data"
    And the tab text and accent color should be blue

  @id:02-agent-tabs-switch-gearup
  Scenario: Switch to GearUp agent
    When I click the "GearUp" tab in the left sidebar
    Then the "GearUp" tab should appear selected/highlighted
    And the active agent label in the header should update to show "GearUp"
    And the chat area should show a welcome message containing "Let's check in on the loyalty program"
    And the tab text and accent color should be gold/yellow

  @id:02-agent-tabs-switch-ignition
  Scenario: Switch to Ignition agent
    When I click the "Ignition" tab in the left sidebar
    Then the "Ignition" tab should appear selected/highlighted
    And the active agent label in the header should update to show "Ignition"
    And the chat area should show a welcome message containing "Campaigns, promotions, engagement"
    And the tab text and accent color should be orange

  @id:02-agent-tabs-switch-partspro
  Scenario: Switch to PartsPro agent
    When I click the "PartsPro" tab in the left sidebar
    Then the "PartsPro" tab should appear selected/highlighted
    And the active agent label in the header should update to show "PartsPro"
    And the chat area should show a welcome message containing "Products, categories, inventory"
    And the tab text and accent color should be green

  @id:02-agent-tabs-switch-diehard
  Scenario: Switch to DieHard agent
    When I click the "DieHard" tab in the left sidebar
    Then the "DieHard" tab should appear selected/highlighted
    And the active agent label in the header should update to show "DieHard"
    And the chat area should show a welcome message containing "Store performance, operations"
    And the tab text and accent color should be red

  @id:02-agent-tabs-switch-back-crew-chief
  Scenario: Switch back to Crew Chief
    Given I have switched to the "DieHard" tab
    When I click the "Crew Chief" tab in the left sidebar
    Then the "Crew Chief" tab should appear selected/highlighted
    And the chat area should show a welcome message containing "I coordinate the full team"
    And the tab text and accent color should be black

  @id:02-agent-tabs-history-preserved
  Scenario: Chat history is preserved when switching tabs
    Given I am on the "Crew Chief" tab
    When I type "hello" in the input and press Enter
    And I wait for the agent to respond (up to 30 seconds)
    And I click the "GearUp" tab
    And then I click back to "Crew Chief"
    Then I should still see my "hello" message and the agent's response
    # Chat history is per-agent and preserved across tab switches

  @id:02-agent-tabs-unread-indicator
  Scenario: Unread indicator appears for background messages
    # NOTE: This scenario applies when Crew Chief fans out to sub-agents.
    # If a sub-agent responds while viewing a different tab, an unread dot appears.
    Given I am on the "Crew Chief" tab
    When I send a question that the Crew Chief will route to multiple agents
    And I switch to a different tab before all responses arrive
    Then tabs with new responses should show an unread indicator (dot or badge)
