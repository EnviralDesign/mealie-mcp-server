# Mealie MCP Workflow Bootstrap

This is not a formal Codex skill yet. It is a working guide for bootstrapping the Mealie import workflow while the MCP server is still evolving.

The manual UI walkthrough lives in `codex/walkthrough_notes.md`. This document is the MCP-first translation: how Codex should approach recipe imports when local API credentials are available, where it should use higher-level tools, where it should drop down to granular tools, and what gaps should drive future MCP changes.

## Operating Assumptions

- Local `.env` contains `MEALIE_URL` and `MEALIE_API_TOKEN`.
- Local tool testing can run directly through `test_cli.py` without a Codex MCP connection.
- The Unraid-hosted Mealie instance may be newer than the checked-in `openapi.json`.
- Prefer live API behavior and `fastmcp inspect` over assuming the local OpenAPI snapshot is current.
- Browser/UI observation is still useful for understanding Mealie behavior, but routine cleanup should move toward MCP/API operations.

## Local Development Loop

Use this loop before relying on the deployed Unraid MCP container:

1. Make local MCP/client changes.
2. Validate import and tool metadata:
   - `uv run python -m compileall src`
   - `uv run fastmcp inspect src/mealie_mcp/server_core.py`
   - `uv run fastmcp inspect src/mealie_mcp/server_full.py`
3. Run live smoke tests against Mealie through `test_cli.py`.
4. For mutating tests, duplicate an existing recipe, mutate the duplicate, then delete it.
5. Record workflow gaps here or in `walkthrough_notes.md`.
6. Commit and push only after local behavior is solid.
7. Let Docker Hub/Unraid rebuild and then do final transport/client testing through the deployed MCP endpoint.

## Tooling Strategy

The new helper tools are workflow tools, not replacements for granular cleanup.

Use workflow tools for the common path:

- `import_or_get_recipe_from_url`
- `formalize_recipe_ingredients`
- `set_recipe_organizers`
- `set_recipe_instructions`
- `get_recipe_cleanup_summary`
- `get_or_create_food`

Use granular tools when judgment or edge cases matter:

- `get_recipe`
- `patch_recipe`
- `update_recipe`
- `parse_ingredient`
- `parse_ingredients`
- `get_foods`, `get_food`, `create_food`, `update_food`, `merge_foods`
- `get_units`, `get_unit`, `create_unit`, `update_unit`, `merge_units`
- category/tag/tool CRUD
- label CRUD in the full profile

## Ideal MCP-First Recipe Import Flow

### 1. Import Or Retrieve

Call `import_or_get_recipe_from_url`.

Expected output is a status plus slug:

- `existing`: recipe already exists by `orgURL`.
- `imported`: Mealie imported a new recipe.

Immediately call `get_recipe` on the slug. Do not assume import quality.

Open or otherwise inspect the live source page for every import. A source page can change after earlier notes, cached snippets, or an OpenAPI snapshot were captured. The live page is the source of truth unless the user says otherwise.

### 2. Initial Quality Summary

Call `get_recipe_cleanup_summary`.

Use the result to quickly determine:

- Whether categories, tags, or tools are missing.
- Whether instructions are one large imported block.
- Whether instruction steps lack ingredient references.
- Whether ingredient records have obvious missing structure.
- Whether linked foods lack metadata such as plural name, description, or label.

This is a triage tool. It does not replace reading the recipe.

### 3. Ingredient Cleanup

Start from the imported recipe's `recipeIngredient` list and original ingredient strings.

Use `formalize_recipe_ingredients` only when it is likely to help. It is useful for parser-driven normalization, but it is still blunt compared with the manual judgment flow.

Ingredient decisions should preserve these heuristics:

- Convert fractions to decimals.
- For spicy/intense ranges, usually choose the low end.
- For base ingredients, consider midpoint or practical cooking amount.
- Prefer canonical grocery items.
- Put prep/form/alternate details into `note`.
- Create a new food only when no existing canonical food is a good match.
- Treat grocery-real distinctions as separate foods when useful, e.g. `fresh basil` versus `dried basil`.

Current granular fallback:

1. Fetch recipe with `get_recipe`.
2. Inspect concise rows with `get_recipe_ingredient_rows`.
3. Resolve foods with `get_foods` / `get_or_create_food`.
4. Resolve units with `get_units`.
5. Repair malformed individual rows with `update_recipe_ingredient_row`, or apply a reviewed decision table with `update_recipe_ingredient_rows`.
6. Add a missing split-out ingredient with `add_recipe_ingredient_row` when a source line combines multiple groceries into one imported row.
7. Remove imported equipment or truly invalid rows with `delete_recipe_ingredient_row`.
8. Use raw `patch_recipe` only as a last resort.

`update_recipe_ingredient_row` is the preferred row-level repair tool for isolated fixes. `update_recipe_ingredient_rows` is preferred when an import brings in unparsed ingredient strings and a reviewed ingredient decision table is ready. Both update by `referenceId`, preserve other rows, and can resolve food/unit names exactly before patching.
`add_recipe_ingredient_row` is for split-row repair, such as a source line that imports as "warm tortillas and smashed avocado" but should become separate tortilla and avocado rows.
`delete_recipe_ingredient_row` is for equipment or invalid rows that should not remain in the grocery ingredient list.

### 4. Food Metadata Enrichment

For any new or weak food records, call `update_food` or `get_or_create_food` with:

- `plural_name`
- `description`
- `label_name` or `label_id`
- `aliases` when a phrase is a genuine alternate name

Food label choices should optimize grocery/shopping behavior, not just culinary taxonomy.

Examples:

- `brown rice noodles` -> label `pasta & noodles`
- `mixed stir fry vegetables` -> label `frozen`
- `flank steak` -> label `meat & seafood`

### 5. Instruction Refactor

If instructions import as a big block or read poorly on a kitchen screen, rewrite them into short linear steps.

Call `set_recipe_instructions` with a list of step objects:

```json
[
  {
    "text": "Make the sauce: combine the garlic, ginger, tamari, honey, rice vinegar, gochujang paste, and toasted sesame oil in a jar. Shake or whisk until smooth.",
    "ingredient_names": ["garlic", "ginger", "tamari", "honey", "rice vinegar", "gochujang paste", "toasted sesame oil"]
  }
]
```

Prefer explicit `ingredient_names` when names resolve cleanly. Use `ingredient_reference_ids` when names are ambiguous.

Use `auto_link_by_text` cautiously. It is helpful as a first pass, but explicit links produce better cooking UX.

Instruction rewrite principles:

- Make each step scan-friendly.
- Keep the cooking sequence linear.
- Avoid huge multi-action blocks.
- Avoid over-fragmenting into tiny steps.
- Link ingredients to the step where they are directly used.
- Do not link every sauce ingredient to later steps that merely say “sauce” unless that helps the cook.

### 6. Organizer Metadata

Call `set_recipe_organizers`.

Use categories for broad navigation:

- `Dinner`
- `Noodles`
- `Breakfast`
- `Dessert`

Use tags for cross-cutting descriptors:

- cuisine or inspiration
- main protein
- speed
- method
- spice level
- dietary notes

Use tools for actual required equipment:

- `skillet`
- `pot`
- `jar`
- `mesh strainer`

Prefer existing organizer records. Use `create_missing=true` only when the new term is clearly useful beyond one recipe.

### 7. Final Validation

Call `get_recipe_cleanup_summary` again.

A good final state usually has:

- Categories present.
- Tags present.
- Tools present.
- No obvious ingredient structure gaps.
- No food metadata gaps for newly created foods.
- Multiple scan-friendly instruction steps.
- Low or zero unlinked instruction steps.
- `one_big_instruction=false`.

Then fetch the full recipe with `get_recipe` and skim the actual fields, because summary tools can miss semantic issues.

Check metadata during this pass:

- `recipeServings`
- `recipeYield`
- `prepTime`
- `cookTime`
- `totalTime`
- image presence
- source URL

Range yields such as `4-6 servings` often need both a numeric `recipeServings` value and a human-readable `recipeYield` string. Prefer preserving the exact yield text in `recipeYield`.

## Optional Pricing Post-Process

Pricing is separate from the base import workflow.

Only consider it after the recipe has clean structured ingredients. The future workflow will likely use the Kroger MCP server to map Mealie foods to purchasable Kroger products and estimate costs.

Current known context:

- Kroger repo: `C:\repos\kroger-mcp-mine`
- Unraid endpoint: `http://192.168.1.2:8003/mcp`
- Preferred store: Kroger Cooper, `03500445`, 5330 S Cooper St, Arlington, TX 76017.
- Kroger preferences now persist under the container token/state directory on Unraid.

Do not block recipe cleanup on pricing.

### Manual Pricing Trial: Chicken Curry

Target recipe:

- `http://192.168.1.2:3000/g/home/r/chicken-curry`

Pricing was manually added on 2026-05-19 after the recipe had already been fully structured.

Resulting description format:

```markdown
---

Price (Kroger, 2026-05-19)

- Total cost: $16.07
- Ingredient costs:
  - Chicken thighs $8.98
  - White onion $0.60
  - Jalapeno $0.09
  - Ginger $0.37
  - Garlic $0.50
  - Vegetable oil $0.12
  - Curry powder $1.03
  - Kosher salt $0.05
  - Tomato paste $0.17
  - Tomato puree $1.08
  - Whole-milk yogurt $0.50
  - Garam masala $0.15
  - Basmati rice $2.03
  - Fresh cilantro $0.40
```

Manual product choices and assumptions:

- White onion: jumbo white onions at `$1.19/lb`; one large onion estimated as `0.5 lb`.
- Jalapeno: fresh jalapenos at `$1.89/lb`; one pepper estimated as `0.05 lb`.
- Ginger: organic ginger root at `$3.99/lb`; `2.5-inch piece` estimated as `1.5 oz`.
- Garlic: loose garlic at `$0.50/ct`; `8 cloves` estimated as one bulb.
- Vegetable oil: Kroger vegetable oil, `$3.79/48 fl oz`; `3 tbsp` equals `1.5 fl oz`.
- Curry powder: Kroger curry powder, `$3.99/1.62 oz`; `2 tbsp` estimated as `0.42 oz`.
- Kosher salt: small seasoning allowance, `$0.05`.
- Tomato paste: Kroger tomato paste, `$0.99/6 oz`; `2 tbsp` estimated as `1 oz`.
- Tomato puree: Kroger tomato puree, `$1.89/28 oz`; `2 cups` estimated as `16 oz`.
- Whole-milk yogurt: Kroger plain whole milk yogurt, `$2.99/32 oz`; `2/3 cup` estimated as `5.33 oz`.
- Chicken thighs: Tyson boneless skinless thighs at `$4.49/lb`; recipe uses `2 lb`.
- Garam masala: Spice Islands garam masala, `$5.49/3 oz`; `1 tsp` estimated as `0.08 oz`.
- Basmati rice: Kroger basmati rice, `$4.99/2 lb`; serving assumption was `2 cups dry rice`, about `13 oz`.
- Fresh cilantro: fresh cilantro bunch at `$0.79/ct`; serving assumption was half a bunch.

Pricing workflow lessons:

- This should stay human-reviewed for now. A useful tool should produce a pricing draft or worksheet, not blindly update the recipe.
- Clean structured Mealie ingredients make the process much easier, but grocery pricing still needs judgment.
- Kroger search results need product selection rules: avoid odd organic-only matches when a conventional item exists, avoid huge bulk sizes unless sensible, and prefer ordinary mid-range store-brand or national-brand products.
- Produce is the most awkward area because Kroger may price by pound, count, or omit price on the best semantic result.
- Quantity-free recipe rows such as `for serving` need explicit assumptions. Those assumptions should either be visible in a draft or stored somewhere more structured than the final description.
- Unit conversion is the biggest friction: tablespoons of spices to ounces, cups to ounces, count-to-weight produce estimates, and vague units such as `piece`.
- The final public description should stay simple, matching the existing style: line separator, date, total, and per-ingredient costs. Product IDs, package sizes, and assumptions are useful for audit but too noisy for the recipe description.

Potential MCP/tool direction:

- Add a Kroger-backed pricing draft helper that accepts a recipe slug and returns candidate products, selected products, conversion assumptions, estimated costs, and uncertainty flags.
- Keep a confirmation step before calling `patch_recipe`.
- Consider storing detailed pricing metadata in recipe `extras` or an external artifact while keeping the human-facing description concise.
- Add explicit uncertainty flags for missing prices, sale prices, quantity-free rows, produce estimates, and hand-estimated density conversions.
- Do not require pricing to be perfect before import/cleanup work can proceed.

## Self-Bootstrapping Rules

When Codex hits a recipe cleanup issue that feels repetitive:

1. Solve the recipe using existing granular tools.
2. Write down the awkward part.
3. Decide whether the MCP server needs:
   - a new workflow tool,
   - a safer granular tool,
   - better diagnostics,
   - better docs/skill instructions,
   - or no code change.
4. Add the smallest useful MCP improvement locally.
5. Validate with a duplicate recipe.
6. Update this document.

Do not prematurely collapse judgment-heavy tasks into opaque automation. The right direction is high-level tools that expose decisions and leave room for granular correction.

## Current Tool Gaps To Watch

- Import should optionally return the full recipe object, not only the slug.
- Ingredient cleanup needs a safer structured tool than raw `patch_recipe`.
- Corpus cleanup now has `get_recipe_ingredient_rows`, `update_recipe_ingredient_row`, `update_recipe_ingredient_rows`, `add_recipe_ingredient_row`, and `delete_recipe_ingredient_row`; keep hardening these as new malformed import patterns appear.
- Alias handling may need dedicated helpers if Mealie exposes richer alias behavior than food update payloads cover.
- Instruction rewriting is still model-authored; the MCP tool only persists structured steps and links.
- `get_recipe_cleanup_summary` should keep learning what is a real gap versus acceptable structure, especially procedural unlinked steps.
- Streaming import endpoints exist in live Mealie but are not implemented in this client yet.
- Image/asset repair is not covered.
- Pricing/Kroger workflow is intentionally separate and not yet integrated.
- Unit create/update now exposes plural display metadata; keep watching for unit cleanup cases because bad unit plurals directly affect ingredient readability.

## Corpus Cleanup Pass Lessons

A live corpus cleanup pass on 2026-05-18 confirmed the MCP-first workflow works well for:

- Food metadata enrichment.
- Organizer backfill.
- Instruction rewrites.
- Ingredient reference linking.

The pass also showed that raw summary metrics can overstate remaining work. A preheat, cooling, resting, or serving step may correctly have no ingredient references. The next summary iteration should distinguish procedural unlinked steps from actionable cooking steps that probably need links.

The hardest remaining corpus issues were malformed ingredient rows, especially cocktail imports and rows like "1 6 ounce" or "1/2 teaspoon" with missing foods. These should be handled through `update_recipe_ingredient_row` or `update_recipe_ingredient_rows`, not ad hoc full-recipe patches.

## New Import Iteration Notes

### Cheesy Zucchini Chicken And Rice Bake

Source:

- `https://www.halfbakedharvest.com/cheesy-zucchini-chicken-and-rice-bake/`

Observed import behavior:

- API import created the recipe and image correctly.
- Servings, prep time, total time, and description imported correctly.
- Cook time was present on the source card but missing after import, so it needed a metadata patch.
- Ingredients imported as raw note/display strings with no structured food or unit rows.
- Instructions imported as one large numbered text block.

Tooling added because of this recipe:

- `get_recipe_ingredient_rows`
- `update_recipe_ingredient_row`
- `update_recipe_ingredient_rows`

Workflow lesson:

- When API import skips ingredient parsing, do not run blind formalization. First parse/source-check the ingredient strings, then apply a reviewed row decision table with `update_recipe_ingredient_rows`.
- Parser output is useful for quantities/units but still needs judgment for canonical foods. Example: parser mapped `salted butter` to existing `unsalted butter`, which was wrong for this recipe.
- Bulk row repair reduced a 17-row manual cleanup into one reviewed operation.

### Honey Mustard Pretzel Chicken And Avocado Bacon Salad

Source:

- `https://www.halfbakedharvest.com/pretzel-chicken-and-avocado-bacon-salad/`

Observed import behavior:

- Same HBH API pattern: image and metadata imported, ingredients remained raw note/display strings, and all instructions collapsed into one numbered block.
- Cook time was present on the source card but missing after import.
- The recipe has repeated foods in distinct contexts, especially `olive oil` and `cayenne pepper`.

Tooling lesson:

- Repeated ingredient foods should be linked by `referenceId`, not by food name. For this recipe, `olive oil` appeared once for brushing chicken and once in dressing; `cayenne pepper` appeared once in the pretzel coating and once in dressing.
- `set_recipe_instructions` now reports `ambiguous_ingredient_matches` when a provided ingredient name maps to multiple reference IDs. Use that response to retry with explicit `ingredient_reference_ids`.

### Sheet Pan Jalapeno Pineapple Shrimp Tacos

Source:

- `https://www.halfbakedharvest.com/jalapeno-pineapple-shrimp-tacos/`

Observed import behavior:

- Same HBH API pattern: image and metadata imported correctly, ingredients stayed raw, and instructions collapsed into one block.
- Cook time was present on the source card but missing after import.
- Source line `warm tortillas and smashed avocado, for serving` combined two separate grocery items into one imported ingredient row.

Tooling added because of this recipe:

- `add_recipe_ingredient_row`

Workflow lesson:

- Some source lines legitimately need to become multiple structured ingredient rows. Update the original row to the primary item, then insert the split-out item immediately after it with `add_recipe_ingredient_row`.
- Duplicate foods in different subcomponents remain common. This recipe required explicit reference IDs for sauce lime/cilantro versus salsa lime/cilantro.

### Greek Chicken Kebabs With Tzatziki Sauce

Source:

- `https://therealfooddietitians.com/greek-chicken-kebabs/`

Observed import behavior:

- Instructions imported as separate steps, unlike the Half Baked Harvest imports.
- Ingredients still imported as raw note/display strings with no structured foods or units.
- Equipment (`6-8 skewers`) imported as an ingredient row.
- Recipe metadata needed source verification: imported servings were `4`, but source says `4-5 servings`; cook time was missing.

Tooling added because of this recipe:

- `delete_recipe_ingredient_row`

Workflow lesson:

- Non-food equipment can enter Mealie as an ingredient. Move it to required tools and remove it from ingredients with `delete_recipe_ingredient_row`.
- Verification should include recipe metadata, not only ingredients and instructions. Servings, yield text, cook time, and total time can import incompletely.

### Chicken Curry

Source:

- `https://www.delish.com/cooking/recipe-ideas/a46444314/best-chicken-curry-recipe/`

Observed import behavior:

- Delish imported the current live 2026 recipe, not the older chicken-thigh/coconut-milk formulation that stale snippets may suggest.
- Instructions imported as six separate steps, but some steps were still too dense for cook mode.
- Ingredients imported as raw note/display strings with no structured foods or units.
- The source yield is `4 - 6 serving(s)`, while Mealie imported only numeric `4` and no yield text.
- A combined serving line (`Basmati rice and chopped fresh cilantro, for serving`) needed to become two structured rows.

Workflow lesson:

- Always verify the current source page before cleanup. Delish in particular may have updated recipe content while preserving the same URL.
- Repair range yields explicitly. For this recipe, `recipeServings=6` and `recipeYield='4-6 servings'` better preserve the source than leaving the imported `4`.
- Mealie regenerates display text from structured quantity/unit/food/note fields after row updates. Preserve the exact source line in `originalText`, and accept that the rendered display may read like structured data rather than editorial prose.
- Use canonical foods for shopping behavior, then keep size/prep qualifiers in notes. Example: create/use `white onion` and put `large, coarsely chopped` in the note.
- Serving garnish lines often need split rows, even when quantities are intentionally zero/blank.

### Ginger Soy Fish

Source:

- `https://rasamalaysia.com/ginger-soy-fish/`

Observed import behavior:

- Image, source URL, servings, prep time, total time, and separate instructions imported correctly.
- Cook time was missing even though the source card says `10 minutes`.
- Ingredients imported as raw note/display strings with no structured foods or units.
- Renaming the recipe from `Ginger Soy Fish Recipe` to `Ginger Soy Fish` changed the slug from `ginger-soy-fish-recipe` to `ginger-soy-fish`.
- The source used dimensional and informal units (`2-inch ginger`, `3 dashes white pepper`) that needed unit metadata cleanup.

Tooling added because of this recipe:

- `create_unit` and `update_unit` now expose plural display metadata (`plural_name`, `plural_abbreviation`, `use_abbreviation`, and `description` where applicable).

Workflow lesson:

- After any `patch_recipe` call that changes `name`, use the slug returned by the response for all subsequent calls. Mealie may regenerate the slug.
- Use canonical grocery foods and preserve source wording in notes/original text. Example: map `cooking oil` to `vegetable oil` and put `(cooking oil)` in the note.
- Unit metadata matters for ingredient readability. Updating `Dashes` to singular `dash` with plural `dashes` immediately fixed the rendered ingredient line.
- Do not automatically add side dishes as ingredients just because instructions mention serving with them. This source says to serve with steamed rice, but rice is not in the ingredient card, so it stayed in the instruction text only.

## Current Confidence

Local direct testing is enough for most MCP development while `.env` is configured.

Deployed MCP testing is still needed before treating a commit as fully shipped because it validates:

- Docker image build.
- Unraid environment variables.
- Streamable HTTP transport.
- Codex MCP client schema handling.
- Any differences between local and container runtime behavior.
