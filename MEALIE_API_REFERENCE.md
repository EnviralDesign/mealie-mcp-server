# Mealie MCP Coverage (Truth Table)

Last updated: 2026-02-17

This document is the source of truth for what this MCP server currently exposes.

## Snapshot

- OpenAPI baseline: `247` endpoints (`/Users/lucas/Documents/mealie-mcp-server/openapi.json`)
- MCP profile counts:
  - `core`: `56` tools
  - `full`: `65` tools
- Primary focus: day-to-day recipe, ingredient/food/unit, and shopping workflows

## Profiles

- `core` (`/Users/lucas/Documents/mealie-mcp-server/src/mealie_mcp/server_core.py`)
  - Lean default profile for clients that cannot selectively disable tools.
- `full` (`/Users/lucas/Documents/mealie-mcp-server/src/mealie_mcp/server_full.py`)
  - Full tool surface from this repo.

## Implemented In MCP (By Domain)

| Domain | Core | Full | Tool Names |
|---|---:|---:|---|
| Recipes (core) | 12 | 12 | `get_recipes`, `get_recipe`, `create_recipe`, `update_recipe`, `patch_recipe`, `delete_recipe`, `duplicate_recipe`, `set_recipe_last_made`, `import_recipe_from_url`, `import_or_get_recipe_from_url`, `test_scrape_url`, `suggest_recipes` |
| Shopping lists | 7 | 7 | `get_shopping_lists`, `get_shopping_list`, `create_shopping_list`, `update_shopping_list`, `delete_shopping_list`, `add_recipe_to_shopping_list`, `remove_recipe_from_shopping_list` |
| Shopping items | 6 | 6 | `get_shopping_items`, `get_shopping_item`, `add_shopping_item`, `add_shopping_items_bulk`, `update_shopping_item`, `delete_shopping_item` |
| Categories | 5 | 7 | `get_categories`, `get_category`, `create_category`, `update_category`, `delete_category` (+ `get_category_by_slug`, `get_empty_categories` in full) |
| Tags | 5 | 7 | `get_tags`, `get_tag`, `create_tag`, `update_tag`, `delete_tag` (+ `get_tag_by_slug`, `get_empty_tags` in full) |
| Tools (equipment) | 6 | 6 | `get_tools`, `get_tool`, `create_tool`, `update_tool`, `delete_tool`, `set_recipe_tools` |
| Foods | 6 | 6 | `get_foods`, `get_food`, `create_food`, `update_food`, `delete_food`, `merge_foods` |
| Units | 6 | 6 | `get_units`, `get_unit`, `create_unit`, `update_unit`, `delete_unit`, `merge_units` |
| Labels | 0 | 5 | `get_labels`, `get_label`, `create_label`, `update_label`, `delete_label` |
| Ingredient parser/formalization | 3 | 3 | `parse_ingredient`, `parse_ingredients`, `formalize_recipe_ingredients` |

## Not Exposed Yet (But Already In Client)

These routes already have client methods in `/Users/lucas/Documents/mealie-mcp-server/src/mealie_mcp/client.py` and are low effort to expose.

| Priority | Domain | Client method(s) | Why it might matter |
|---|---|---|---|
| High | Recipe bulk actions | `bulk_tag_recipes`, `bulk_categorize_recipes`, `bulk_delete_recipes`, `bulk_export_recipes`, `bulk_update_recipe_settings` | Useful for mass cleanup / migration workflows |
| Medium | Shopping item bulk delete | `delete_shopping_items_bulk` | Fast list cleanup; should be reviewed before exposing |
| Medium | Organizer lookup helper | `get_tool_by_slug` | Better discovery for tool entities |

## Not Implemented In Client (Deferred)

Representative deferred areas from OpenAPI scope:

- Recipe images/assets upload/update lifecycle
- Mealplans, mealplan rules, cookbooks
- Comments/timeline/exports/shared workflows
- Group/household management and invitations
- Admin/debug/backups/email/system endpoints

## Notes On Intentional Constraints

- `core` is optimized for day-to-day use and token efficiency.
- `full` is intended for broader management workflows where clients can handle larger tool metadata.
- Bulk/destructive endpoints are deferred unless they clearly improve normal user workflows.
- Preference remains: recipes by slug; most organizer entities by ID.
