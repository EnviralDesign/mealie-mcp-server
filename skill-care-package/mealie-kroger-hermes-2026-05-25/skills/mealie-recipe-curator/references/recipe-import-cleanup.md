# Recipe Import And Cleanup

## Import

Call `import_or_get_recipe_from_url` when available. If the recipe already exists by `orgURL`, use the existing slug rather than creating a duplicate. After import, immediately call `get_recipe`.

Do not assume ingredients parsed correctly, instructions split correctly, image imported, times imported, servings/yield imported, or source page content matches older notes.

Open or otherwise inspect the live source page when importing from a URL. The live source is authoritative unless the user provides a different source of truth.

## Triage

Call `get_recipe_cleanup_summary` when available. Treat it as triage, not truth.

Look for one large instruction block, missing categories/tags/tools, unlinked instruction steps, missing food/unit structure, weak food metadata, equipment imported as an ingredient, missing times, missing image/source URL, and range yields flattened to one number.

## Ingredient Repair

Use `get_recipe_ingredient_rows` to inspect concise rows. Prefer `update_recipe_ingredient_row` for isolated fixes and `update_recipe_ingredient_rows` for reviewed decision tables.

Use `add_recipe_ingredient_row` when a source line combines separate groceries, e.g. tortillas and avocado. Use `delete_recipe_ingredient_row` when the row is equipment or invalid.

Use raw `patch_recipe` only when no safer row-level tool exists.

## Metadata Repair

Verify and repair `name`, `recipeServings`, `recipeYield`, `prepTime`, `cookTime`, `totalTime`, `orgURL`, and image presence.

For range yields such as `4-6 servings`, store a practical numeric serving value in `recipeServings` and preserve the range text in `recipeYield`.

If renaming a recipe changes its slug, use the slug returned by the response for all subsequent calls.

## Known Import Patterns

Half Baked Harvest imports often preserve image and metadata but leave ingredients as raw strings and collapse instructions into one numbered block.

Some non-HBH imports split instructions but still leave ingredients unstructured.

Equipment can import as an ingredient. Move it to required tools.

Serving lines often need split rows even when quantities are intentionally blank.

