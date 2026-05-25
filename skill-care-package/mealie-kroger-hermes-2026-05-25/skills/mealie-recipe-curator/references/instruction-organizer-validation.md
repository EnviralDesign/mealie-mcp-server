# Instructions, Organizers, And Validation

## Instruction Rewrite

Rewrite imported instructions into short, scan-friendly steps for a phone in the kitchen.

Good steps are linear, action-oriented, not huge multi-action paragraphs, and not over-fragmented into trivial micro-steps.

Use `set_recipe_instructions` when available. Prefer explicit ingredient references. Use `ingredient_reference_ids` when a food appears multiple times in different recipe components.

Do not link every sauce ingredient to later steps that merely say "add sauce" unless it helps the cook. Link ingredients where they are directly used.

Procedural steps such as preheat, rest, cool, serve, or store may correctly have no linked ingredients.

## Organizers

Use categories for broad navigation: `Dinner`, `Breakfast`, `Dessert`, `Beverage`, `Noodles`.

Use tags for cross-cutting traits: cuisine/inspiration, main protein, speed, method, dietary notes, spice level.

Use tools for actual equipment: `skillet`, `pot`, `jar`, `mesh strainer`, `cocktail shaker`.

Prefer existing organizers. Create missing terms only when they are likely reusable.

## Final Validation

After mutations, refetch the recipe and check categories/tags/tools, structured ingredients, food metadata for new foods, instruction readability, ingredient references, servings/yield/time, image, and source URL.

Then run summary tooling again if available. Treat summary output as a signal to inspect, not as a substitute for review.

