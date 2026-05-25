---
name: mealie-shopping-list-operator
description: Manage Mealie shopping lists through MCP/API. Use when Codex or Hermes needs to inspect active lists, add groceries, update or normalize existing list items, create structured foods only when appropriate, attach labels, avoid duplicates, preserve checked items, or convert note-only shopping entries into canonical food plus note patterns.
---

# Mealie Shopping List Operator

Use this skill for Mealie shopping list tasks. Use `mealie-recipe-curator` for recipe ingredient cleanup and recipe metadata work.

## Core Loop

1. List shopping lists and choose the active/current list. Prefer the list updated today or named `Shop` when the user does not specify.
2. Fetch the full list before mutating.
3. Detect existing unchecked items to avoid duplicates.
4. Decide whether each requested item should be structured food or note-only.
5. Create or enrich food records only when the item is specific enough.
6. Add or update list items.
7. Refetch the list and verify display, food, note, label, and checked state.

## Canonical Food Policy

Create or link a food when the item is specific and likely reusable:

- `cucumber`
- `bell pepper` with note `orange`
- `2% milk`
- `almond milk`
- `whole bean coffee`
- `frozen pizza`
- `mozzarella cheese sticks`
- `beer` with brand in the note
- `cereal` with quality guidance in the note

Use note-only items when the request is generic, open-ended, or a shopping instruction:

- `Bread`
- `Fresh fruits`
- `Box of salad`
- `Sliced turkey or chicken`
- `snacks for school`
- `something easy for Friday dinner`

The guiding rule: structure the thing a shopper or future recipe would reuse; keep brand, quality, prep, and choice constraints in `note`.

## Mutation Rules

- Upgrade existing note-only items when they clearly match the new request.
- Preserve checked items unless the user asks to reopen them.
- Do not create duplicate active items.
- Use labels to keep the shopping UI organized even for note-only items.
- Refetch after writes; Mealie display text may differ from the payload.

## References

Read as needed:

- `references/shopping-list-workflow.md` for concrete MCP operations.
- `references/canonical-food-policy.md` for structured-food versus note-only decisions.
- `references/examples.md` for common transformations.
