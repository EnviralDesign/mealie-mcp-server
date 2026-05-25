---
name: mealie-recipe-curator
description: Import, repair, enrich, and validate Mealie recipes through MCP/API. Use when Codex or Hermes needs to import recipe URLs, clean existing recipes, formalize structured ingredients, enrich food/unit metadata, rewrite instructions for cook mode, attach ingredient references to steps, assign categories/tags/tools, or audit a Mealie recipe corpus.
---

# Mealie Recipe Curator

Use Mealie MCP/API first. Use the browser only when source verification, image checks, cook-mode observation, or UI-only behavior matters.

## Core Loop

1. Fetch or import the recipe.
2. Refetch the full recipe immediately; never trust import quality.
3. Check source/current page when importing from the web.
4. Triage with cleanup summary tools when available.
5. Repair ingredients, food metadata, instructions, organizers, and metadata.
6. Refetch and validate after mutations.

Use narrow mutation tools before full recipe patches. Preserve user-authored data and unrelated recipe fields.

## Preferred Tools

Use workflow tools for the common path:

- `import_or_get_recipe_from_url`
- `get_recipe_cleanup_summary`
- `formalize_recipe_ingredients`
- `set_recipe_instructions`
- `set_recipe_organizers`
- `get_or_create_food`

Use granular tools for edge cases:

- `get_recipe`
- `patch_recipe`
- `update_recipe`
- `get_recipe_ingredient_rows`
- `update_recipe_ingredient_row`
- `update_recipe_ingredient_rows`
- `add_recipe_ingredient_row`
- `delete_recipe_ingredient_row`
- `get_foods`, `get_food`, `create_food`, `update_food`, `merge_foods`
- `get_units`, `get_unit`, `create_unit`, `update_unit`, `merge_units`

## Decision Rules

- Prefer canonical grocery foods over every adjective in the source phrase.
- Put prep, quality, alternate, and brand details in ingredient `note`.
- Create foods only when no existing canonical food is suitable.
- Keep grocery-real distinctions when shopping differs, e.g. `fresh basil` versus `dried basil`.
- Convert fractions to decimals.
- For spicy/intense ranges, usually choose the low end.
- For base ingredients, choose a practical cooking amount or midpoint.
- Split combined source rows when they represent separate grocery items.
- Move equipment out of ingredients and into required tools.
- Link instruction steps to the ingredients directly used in that step.

## References

Read only what the task needs:

- `references/recipe-import-cleanup.md` for the full import/cleanup workflow.
- `references/ingredient-decisions.md` for ingredient parsing and canonical-food judgment.
- `references/instruction-organizer-validation.md` for cook-mode instructions, organizers, and final validation.

