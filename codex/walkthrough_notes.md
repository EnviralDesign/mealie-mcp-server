# Mealie Recipe Import Walkthrough Notes

These notes capture the manual UI process for importing and cleaning up a recipe in Mealie. They are intentionally written from the human workflow perspective. Later, this should be translated into an MCP-first workflow and eventually into a Codex skill once the MCP server has the right tools.

Example walkthrough recipe:

- Source URL: `https://www.halfbakedharvest.com/korean-beef-sesame-noodles/`
- Imported recipe: `20 Minute Korean Beef Sesame Noodles`
- Mealie slug: `20-minute-korean-beef-sesame-noodles`

## High-Level Goal

The goal is not just to import a recipe that looks readable. The goal is to create structured recipe data that is useful in the kitchen today and useful later for shopping, inventory, meal planning, ingredient overlap, and cost optimization.

Good imported recipes should have:

- Structured ingredients with correct quantities, units, food records, and notes.
- Canonical food choices where possible.
- Useful prep or qualifier notes where needed.
- Clean, scan-friendly instruction steps.
- Ingredient references linked to each relevant instruction step.
- Reasonable categories, tags, and tools.
- Enriched food metadata for any new food records created during cleanup.

## Manual UI Import Flow

1. Open Mealie.
2. Click `Create`.
3. Choose `Import`.
4. Paste the recipe URL.
5. Leave `Parse recipe ingredients after import` enabled.
6. Click `Create`.
7. After import, Mealie opens the new recipe and starts the ingredient parser review flow.

Observed import behavior:

- The image imported correctly for the test recipe.
- The recipe initially imported instructions as one large numbered text block.
- Ingredient parsing worked partially, but needed human judgment for food canonicalization and notes.

## Ingredient Parser Review

The parser shows one uncertain ingredient at a time, with:

- Original ingredient text.
- Confidence score.
- Quantity.
- Unit.
- Food.
- Notes.
- Optional button to create a missing food.
- Optional button to add an alias after selecting a different existing food.

Manual process for each ingredient:

1. Read the original ingredient text first.
2. Confirm quantity and unit.
3. Search the food field for a good existing canonical item.
4. If a good existing item exists, select it.
5. If no good match exists, create a new food record.
6. Put preparation details, alternates, and useful qualifiers in `Notes`.
7. Click `Next`.
8. On the final review screen, scan every parsed ingredient before saving.

## Ingredient Heuristics

### Quantity

Mealie stores quantities structurally, so fractional recipe text is converted to decimals.

Examples:

- `1/2 cup` becomes `0.5`.
- `1/4 cup` becomes `0.25`.

For ranges, choose a practical structured quantity:

- For spicy or intense ingredients, use the low end.
  - `2-3 tablespoons Gochujang` became `2 tablespoons`.
- For base ingredients, consider a midpoint or most practical amount.
  - Example for future judgment: rice, pasta, vegetables, or stock might not always want the low end.

The important rule is to make a reasonable cooking decision, not preserve ambiguity that hurts shopping and scaling.

### Unit

Use existing structured units when the parser finds them correctly.

Examples from walkthrough:

- `tablespoon`
- `cup`
- `ounce`
- `pound`
- `clove`

If the unit is missing but the original text clearly has one, search/select it before creating anything new.

### Food

Food should generally be the canonical grocery or pantry item, not every adjective in the original ingredient text.

Examples:

- Original: `1 tablespoon chopped fresh ginger`
  - Food: `ginger`
  - Notes: `fresh, chopped`
- Original: `2-3 tablespoons Gochujang (Korean chili paste)`
  - Existing food selected: `gochujang paste`
  - Notes: `(Korean chili paste)`
- Original: `1 pound flank steak or chicken breast, sliced thin`
  - Food: `flank steak`
  - Notes: `or chicken breast, sliced thin`

However, canonicalization should respect grocery reality. Some terms that look like qualifiers are separate purchasable items.

Example:

- `fresh basil` and `dried basil` are materially different grocery items.
- In this walkthrough, existing foods included `fresh basil` and `dried basil`, but not plain `basil`.
- Keeping `fresh basil` as the food was correct.

### Notes

The `Notes` field is a freeform string. It should contain useful cooking or shopping context not represented by quantity/unit/food.

Good notes:

- Prep state: `chopped`, `sliced`, `sliced thin`, `toasted`.
- Freshness or form when meaningful: `fresh, chopped`.
- Alternate acceptable ingredient: `or soy sauce`, `or chicken breast, sliced thin`.
- Parenthetical synonym/context when the original gives an alternate name: `(Korean chili paste)`.

Avoid putting context in notes when it does not help the user cook or shop.

Example:

- `Korean chili paste` is basically an explanatory synonym for gochujang paste, so it is better as `(Korean chili paste)` than a plain note that reads like prep.

### Aliases

After selecting an existing food instead of creating a new one, Mealie may offer an alias action.

Example:

- Selected `ginger` for original `fresh ginger`.
- UI offered `Add "fresh ginger" as alias for ginger`.

This is important for future automation. Alias creation may improve future parser matches and reduce duplicate foods. Do not blindly add aliases, but consider them when the original phrase is a genuine alternate name for the selected food.

## Walkthrough Ingredient Decisions

### `1 tablespoon chopped fresh ginger`

- Quantity: `1`
- Unit: `tablespoon`
- Food searched: `ginger`
- Existing food selected: `ginger`
- Notes changed from `chopped` to `fresh, chopped`

Reasoning:

- `ginger` is the canonical item.
- `fresh` and `chopped` are useful prep/form notes.

### `1/2 cup tamari or soy sauce`

- Quantity: `0.5`
- Unit: `cup`
- Food: `tamari`
- Notes: `or soy sauce`

Reasoning:

- `tamari` is the primary ingredient.
- `or soy sauce` is a useful alternate.

### `2-3 tablespoons Gochujang (Korean chili paste)`

- Quantity: `2`
- Unit: `tablespoon`
- Food searched: `gochujang`
- Existing food selected: `gochujang paste`
- Notes: `(Korean chili paste)`

Reasoning:

- Use the low end because it is spicy.
- Existing `gochujang paste` was a good match.
- Parentheses preserve alternate name/context.

### `8 ounces brown rice noodles`

- Quantity: `8`
- Unit: `ounce`
- Search results included `wide rice noodles` and `instant ramen noodles`, but neither was a good match.
- Created food: `brown rice noodles`
- Notes: blank

Reasoning:

- `brown rice noodles` is specific and grocery-real.
- Do not choose a different noodle type just to avoid creating a food.

### `3 cups mixed stir fry vegetables`

- Quantity: `3`
- Unit: `cup`
- Search did not find a good existing item.
- Created food: `mixed stir fry vegetables`
- Notes: blank

Reasoning:

- This is a grocery-level item, likely a pre-cut or frozen blend.
- It should be its own food rather than `vegetable oil`, `vegetable stock`, or a generic `vegetables` record.

### `1 pound flank steak or chicken breast, sliced thin`

- Quantity: `1`
- Unit: `pound`
- Food: `flank steak`
- Notes changed to `or chicken breast, sliced thin`

Reasoning:

- Flank steak is primary.
- Chicken breast is an alternate protein, not the canonical food for this recipe.
- `sliced thin` is prep detail.

## Final Ingredient Review

After the individual parser items, Mealie shows a final review screen with every ingredient. Use this to catch:

- Missing food records.
- Missing notes.
- Incorrect canonicalization.
- Fractional quantities converted incorrectly.
- Prep words accidentally swallowed into food names.
- Good food names that should be split into food plus notes.

Example review issue:

- `fresh basil` looked like it might be better as `basil` plus note `fresh`.
- Existing food records showed `fresh basil` and `dried basil`, but not plain `basil`.
- Because those are separate grocery items, leaving food as `fresh basil` was correct.

## Instruction Cleanup

After saving parsed ingredients, the recipe page showed the instructions imported as one large numbered block.

Manual UI route:

1. Click recipe `Edit`.
2. Open `JSON`.
3. Edit `recipeInstructions` directly.

During walkthrough, direct JSON editing was skipped in favor of calling the authenticated Mealie API from the browser context. The underlying operation was equivalent to patching the recipe JSON.

Original imported instruction problem:

- One `recipeInstructions` item contained all five numbered instructions.
- No `ingredientReferences` were attached.

Cleanup goal:

- Rewrite into short, linear, scan-friendly steps.
- Preserve recipe meaning.
- Avoid over-fragmenting into tiny actions.
- Attach ingredient references to each step.

Rewritten steps for walkthrough:

1. Make the sauce: combine the garlic, ginger, tamari, honey, rice vinegar, gochujang paste, and toasted sesame oil in a jar. Shake or whisk until smooth.
2. Cook the brown rice noodles according to package directions. Drain and rinse under cold water.
3. Heat 1 tablespoon sesame oil in a large skillet over high heat. Add the mixed stir fry vegetables and cook until wilted, 2 to 3 minutes.
4. Stir 2 tablespoons of the sauce into the vegetables and cook until coated, then transfer the vegetables out of the skillet.
5. Add the remaining 1 tablespoon sesame oil to the same skillet. Add the shallots and cook until deeply softened, about 2 minutes.
6. Add the flank steak and let it sear undisturbed for 2 minutes, then toss to separate.
7. Pour in the remaining sauce and simmer for 1 minute. Stir in the noodles and vegetables, then cook for 2 to 3 minutes, until the sauce coats the noodles.
8. Remove from heat and stir in the fresh basil and toasted sesame seeds. Serve topped with more fresh basil.

## Ingredient Reference Linking

Mealie supports linking ingredients to individual instruction steps. In Cook Mode, linked ingredients appear visually above each step.

This is very useful because:

- It shows what to gather for the current step.
- It reduces scanning load on a phone or tablet in the kitchen.
- It makes the recipe more structured for future automation.

Reference strategy:

- Link ingredients that are directly used in the step.
- Link fewer high-confidence ingredients rather than broad guesses.
- Do not link every sauce ingredient to every later step that says “sauce” unless that is desired for cooking UX.

Walkthrough linking:

- Step 1 linked sauce ingredients:
  - garlic
  - ginger
  - tamari
  - honey
  - rice vinegar
  - gochujang paste
  - toasted sesame oil
- Step 2 linked:
  - brown rice noodles
- Step 3 linked:
  - sesame oil
  - mixed stir fry vegetables
- Step 4 linked:
  - mixed stir fry vegetables
- Step 5 linked:
  - sesame oil
  - shallot
- Step 6 linked:
  - flank steak
- Step 7 linked:
  - brown rice noodles
  - mixed stir fry vegetables
- Step 8 linked:
  - fresh basil
  - sesame seeds

Cook Mode confirmed the effect: each step card displayed only its linked ingredients above the instruction text.

## Categories, Tags, And Tools

Manual UI process:

- In edit mode, categories/tags/tools work like food fields.
- Typing searches existing records.
- If no match exists, there is a create action.

Walkthrough recipe initially had:

- Categories: none
- Tags: none
- Tools: none

Existing organizer data was sparse:

- Categories included `beverage`, `instapot`, `pasta`, `One pan`.
- Tags were empty.
- Tools included `mesh strainer`, `oven pan`, `instapot`.

Starter metadata added:

- Categories:
  - `Dinner`
  - `Noodles`
- Tags:
  - `Korean-inspired`
  - `beef`
  - `quick`
  - `stir fry`
  - `spicy`
- Tools:
  - `skillet`
  - `pot`
  - `jar`
  - `mesh strainer`

Heuristics:

- Categories should be broad, navigational buckets.
- Tags can be more descriptive and cross-cutting.
- Tools should be kitchen equipment actually required or strongly implied by the instructions.
- Avoid excessive tags.
- Prefer existing organizer records when they make sense.

## Food Metadata Enrichment

After parsing and recipe cleanup, review any new food records created during import.

In Data Management > Foods, food records generally have:

- Name
- Plural Name
- Description
- Label
- On Hand

Existing examples:

- `garlic`
  - Plural: `garlic`
  - Description: `Garlic bulbs contain pungent, flavorful cloves used to season a wide range of savory dishes.`
  - Label: `produce`
- `flank steak`
  - Plural: `flank steaks`
  - Description: `Lean, flavorful cut of beef from the lower chest, often used for grilling or stir-fries.`
  - Label: `meat & seafood`
- `gochujang paste`
  - Plural: `gochujang paste`
  - Description: `Korean fermented red chili paste with a savory, sweet, and spicy flavor, used as a condiment or in sauces.`
  - Label: `condiments`

New food records from walkthrough:

### `brown rice noodles`

Updated metadata:

- Plural Name: `brown rice noodles`
- Description: `Gluten-free rice noodles made from brown rice, used in stir-fries, soups, and noodle bowls.`
- Label: `pasta & noodles`

### `mixed stir fry vegetables`

Updated metadata:

- Plural Name: `mixed stir fry vegetables`
- Description: `Mixed vegetable blend for stir-fries, often sold frozen or pre-cut for quick cooking.`
- Label: `frozen`

Reasoning:

- Food metadata matters for grocery organization and future shopping/inventory workflows.
- Labels should reflect where the item is likely purchased.
- Some items could reasonably fit multiple labels. Choose the most helpful grocery behavior.

## Pricing Post-Process

Some older recipes may have a pricing breakdown embedded in the recipe description. This was part of a separate initiative using the Kroger MCP server.

Current related repo and deployment:

- Local repo: `C:\repos\kroger-mcp-mine`
- Unraid container: `kroger-mcp`
- Streamable HTTP endpoint: `http://192.168.1.2:8003/mcp`
- Container was observed running but marked unhealthy during this walkthrough.

This should stay conceptually separate from the base recipe import/setup flow. The base flow should produce clean structured recipes first. Pricing can then run as an optional post-process once ingredient records are structured enough to search Kroger products.

Likely future pricing workflow:

1. Start from a cleaned Mealie recipe.
2. Extract structured ingredients.
3. Query Kroger products for likely purchasable matches.
4. Pick best product/package matches.
5. Estimate recipe cost from package price and used quantity.
6. Store or render a pricing breakdown in the recipe description or another suitable metadata field.

This is lower priority than reliable import, ingredient cleanup, instruction cleanup, linking, organizer metadata, and food metadata enrichment.

## MCP Translation Notes

The manual flow points to several MCP tool needs.

### Existing useful MCP capabilities

The current MCP server already has some relevant tools:

- Import recipe from URL.
- Get recipe.
- Patch recipe.
- Search/list/create foods.
- Search/list/create units.
- Parse ingredients.
- Formalize recipe ingredients.
- Get/list/create categories, tags, tools.
- Set recipe tools.

### First-pass MCP support added after walkthrough

The first source-first pass added tools that map directly to the manual cleanup pain points:

- `set_recipe_organizers`
  - Sets categories, tags, and tools by IDs and/or exact names.
  - Can create missing organizer records.
  - Replaces only the organizer groups supplied.
- `set_recipe_instructions`
  - Replaces the imported instruction list with clean structured steps.
  - Accepts explicit `ingredient_reference_ids` or human-readable `ingredient_names`.
  - Can optionally auto-link ingredients by step text.
- `get_recipe_cleanup_summary`
  - Reports missing categories/tags/tools.
  - Flags one-large-instruction imports and unlinked steps.
  - Lists ingredient structure gaps and food metadata gaps.
- `get_or_create_food`
  - Finds a canonical food by exact normalized name or creates it.
  - Can fill plural name, description, label, and aliases.
- `create_food` and `update_food`
  - Now support plural name, label ID/name, aliases, and label creation control.

### Tool gaps or improvement areas

Useful future MCP capabilities:

- Import URL and immediately return the created recipe object.
- Dedupe imported recipes by `orgURL`.
- Formalize ingredients with better heuristics:
  - Search existing foods.
  - Preserve prep/qualifier notes.
  - Handle ranges based on ingredient type.
  - Suggest aliases.
  - Create missing foods only when needed.
- Enrich newly created foods:
  - plural name
  - description
  - grocery label
  - maybe aliases
- Get available labels and map food labels reliably.
- Improve recipe instruction rewriting from source text automatically.
- Run a final recipe quality check and report:
  - newly created foods
  - uncertain parsing choices
  - ambiguous ingredient references

### Likely ideal automated workflow

1. Import or retrieve recipe from URL.
2. Fetch full recipe object.
3. Parse/formalize ingredients.
4. For each ingredient:
   - choose quantity/unit/food/notes
   - create food if needed
   - optionally add alias
5. Save structured ingredients.
6. Rewrite instructions into clean steps.
7. Link ingredients to steps.
8. Add categories, tags, and tools.
9. Enrich newly created food records.
10. Re-fetch recipe and validate final state.
11. Report decisions, creations, and any uncertainties.

## Open Judgment Points

These should remain explicit in the future skill/tooling workflow:

- When to create a new food versus selecting a close existing one.
- When a qualifier belongs in food name versus notes.
- When an alternate ingredient should be notes versus a separate recipe variant.
- Whether to add aliases automatically or ask first.
- Whether labels should follow grocery location or culinary category.
- How aggressive to be when rewriting instructions.
- Whether to link sauce ingredients only at sauce-making step or also later sauce-use steps.
- How to handle imported images when missing or poor quality.

## Current Recipe Final State Summary

For the walkthrough recipe:

- Imported from URL successfully.
- Image imported successfully.
- Ingredients were parsed and manually cleaned.
- Two foods were created:
  - `brown rice noodles`
  - `mixed stir fry vegetables`
- Created foods were enriched after recipe cleanup.
- Instructions were rewritten from one block into 8 steps.
- Ingredient references were linked to each step.
- Cook Mode verified the linked ingredient display.
- Categories, tags, and tools were added.
