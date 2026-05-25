# Mealie/Kroger Hermes Skill Care Package

Created: 2026-05-25

This package contains draft first-class skills for a Hermes agent that needs to work with the household Mealie and Kroger MCP workflows.

## Skills

- `skills/mealie-recipe-curator`
  - Import recipes from URLs.
  - Clean structured ingredients and food metadata.
  - Rewrite recipe instructions for cook mode.
  - Attach ingredients to steps.
  - Assign categories, tags, and required tools.

- `skills/mealie-shopping-list-operator`
  - Inspect active shopping lists.
  - Add requested groceries.
  - Use structured foods only when useful.
  - Keep generic shopping requests as note-only items.

- `skills/kroger-grocery-operator`
  - Search Kroger products at the preferred store.
  - Price recipe ingredients.
  - Understand package sizes and cart safety.
  - Maintain awareness of persistent Kroger MCP state.

- `skills/mealie-meal-plan-optimizer`
  - Draft meal plans from Mealie recipes.
  - Compare random and curated plans.
  - Optimize for ingredient overlap, cost, waste, effort, and variety.

## Preferred Store

Kroger Cooper:

- `location_id`: `03500445`
- address: `5330 S Cooper St, Arlington, TX 76017`

## Installation Notes

Each subdirectory under `skills/` is a standalone skill with its own `SKILL.md`, optional `agents/openai.yaml`, and references.

Point the agent or installer at this package, or copy individual skill directories into the target skill location.

No API keys, tokens, credentials, or secrets are included in this package.
