# Mealie Corpus Cleanup Pass - 2026-05-18

This report captures the live corpus cleanup pass run after the manual import walkthrough and first MCP workflow-tool additions.

The user confirmed a full backup before live mutation work began.

## Scope

Corpus at start of pass:

- 49 recipes.
- 242 food records.
- Food metadata gaps were present on 47 food records.
- 48 recipes were missing at least one organizer group.
- 47 recipes had at least one unlinked instruction step.

Work intentionally excluded:

- Kroger/pricing cleanup.
- Recipe images/assets.
- Deep row-level ingredient repairs where the imported row is semantically malformed.

## Sub-Agent Lanes

Mini agents were used in separate lanes:

- Food metadata lane: scanned and updated food records only.
- Instruction structure lane: audited and rewrote selected recipe instructions only.
- Ingredient-linking lane: attached ingredient references to existing steps only.
- Organizer taxonomy lane: audited and backfilled categories, tags, and tools only.

The lanes were kept separate to avoid conflicting writes.

## Food Metadata

Completed:

- Scanned all 242 food records.
- Filled plural name, description, and label metadata for all records that were missing it.
- Added missing grocery labels:
  - `beverages`
  - `household`
- Cleaned up beverage/household edge cases:
  - `Pear liquor ` -> `pear liqueur`, with alias `pear liquor`
  - `Orange liquor ` -> `orange liqueur`, with alias `orange liquor`
  - `Gin` -> `gin`
  - `water` labeled as `beverages`
  - household items labeled as `household`

Current state:

- 242 foods scanned.
- 0 food records missing plural name, description, or label.
- 0 recipe-referenced food metadata gaps.

## Organizer Taxonomy

Completed:

- Backfilled categories, tags, and required tools across the corpus.
- Remaining organizer gaps after final pass: 0.

Core category set now in use:

- `Dinner`
- `Breakfast`
- `Dessert`
- `Beverage`
- `Side`
- `Snack/Bread`

Examples of normalized or added tags:

- Cuisine: `Italian`, `Thai`, `Korean`, `Indian`, `Japanese`, `Brazilian`, `Cajun`, `Southern`
- Protein: `beef`, `chicken`, `pork`, `shrimp`, `salmon`, `tofu`, `turkey`, `sausage`, `scallops`, `tilapia`
- Method/form: `stir-fry`, `one-pot`, `sheet-pan`, `baked`, `instant-pot`, `scampi`, `quiche`, `meatloaf`, `grain-bowl`, `lettuce-wraps`
- Other: `quick`, `spicy`, `cocktail`, `pie`, `cake`, `fruit`, `noodles`, `pasta`, `rice`

Tools added or normalized:

- `Instant Pot`
- `cocktail shaker`
- `mixing bowl`

Existing organizer records normalized:

- `Korean-inspired` -> `Korean`
- `stir fry` -> `stir-fry`
- `beverage` -> `Beverage`

Remaining organizer cleanup to consider:

- Legacy category `instapot` appears obsolete now that `Instant Pot` is a tool and `instant-pot` is a tag.
- Legacy categories `Noodles`, `pasta`, and `One pan` are likely orphaned or better represented as tags.
- Legacy tool `instapot` may be redundant with `Instant Pot`.

## Instruction Rewrites

Recipes rewritten into cleaner scan-friendly steps:

- `strawberry-rhubarb-pie`
- `hummingbird-cake`
- `sweet-and-sour-couscous-stuffed-peppers`
- `chicken-and-broccoli-with-white-sauce`
- `turkey-meatloaf-squares-with-sweet-potatoes`
- `lightened-up-shrimp-scampi`
- `mushroom-orzo-with-lemon-parmesan`
- `chicken-katsu-with-ginger-rice`
- `easy-lasagna`

All rewrites were done by updating `recipeInstructions` only.

## Ingredient Reference Linking

Recipes where ingredient references were attached to existing steps without rewriting instruction text:

- `glass-noodles-with-ground-pork-and-chili`
- `pad-thai`
- `ramen-coleslaw`
- `garlic-butter-oven-baked-tilapia`
- `baked-salmon-fillets-dijon`
- `ground-beef-pasta-skillet`
- `easy-indian-butter-chicken`
- `spinach-tomato-and-feta-quiche`
- `good-old-fashioned-pancakes`
- `pasta-all-amatriciana`
- `instant-pot-spaghetti-and-meat-sauce`
- `one-pot-spaghetti-with-meat-sauce`
- `spicy-thai-basil-chicken-pad-krapow-gai`
- `italian-chicken-sheet-pan-supper`
- `chana-masala-savory-indian-chick-peas`
- `chicken-parmigiana`
- `sweet-and-spicy-chicken`
- `garlic-chili-noodles`
- `bibimbap-korean-rice-bowl`
- `life-changing-instant-pot-beef-stew`
- `brazilian-cheese-bread-recipe-pao-de-queijo`
- `fettuccine-with-walnuts-and-parsley`
- `baked-pork-chops`
- `cajun-spiced-tofu-tostadas-with-beet-crema`
- `pork-and-pineapple-grain-bowl`
- `sheet-pan-smoked-sausage-apple-and-root-veggie-dinner`

Remaining unlinked steps were generally procedural, serving, preheat, cooling, or section-transition steps, but the summary tool still counts them as unlinked.

## Final Metrics

Final corpus summary:

- Recipes: 49
- Food metadata gaps: 0
- Organizer gaps: 0
- Recipes with at least one unlinked step: 34
- Total unlinked steps reported by summary: 95
- Fully linked recipes by raw summary count: 15
- Recipes with ingredient-row gaps: 11
- Total ingredient-row gaps: 29

The raw unlinked-step count overstates remaining work because it includes procedural steps that do not directly consume ingredients. The summary tool should eventually distinguish "unlinked actionable ingredient step" from "unlinked procedural step."

## Remaining Focus Areas

### Ingredient Rows

Remaining ingredient-row gaps are concentrated in 11 recipes. These are not simple metadata gaps. Most require semantic row repair:

- `best-spicy-marg-ever`
- `whiskey-apple-sour`
- `easy-lasagna`
- `garlic-butter-oven-baked-tilapia`
- `instant-pot-butternut-squash-beef-stew`
- `lightened-up-shrimp-scampi`
- `lemon-parmesan-chicken-with-arugula-salad-topping`
- `mushroom-orzo-with-lemon-parmesan`
- `hummingbird-cake`
- `garlic-lime-shrimp`
- `chicken-katsu-with-ginger-rice`

These should be handled with a future row-level ingredient repair workflow rather than raw `patch_recipe` edits.

### Instruction/Linking Remainder

High-remaining raw unlinked counts:

- `sweet-and-spicy-chicken`: many remaining procedural or low-confidence steps.
- `lemon-parmesan-chicken-with-arugula-salad-topping`: also has an ingredient-row gap.
- `instant-pot-butternut-squash-beef-stew`: also has ingredient-row gaps.
- `instant-pot-hoppin-john`
- `life-changing-instant-pot-beef-stew`
- `good-old-fashioned-pancakes`
- `chicken-cucumber-lettuce-wraps-with-peanut-sauce`

Some may need instruction rewrites; some may only need the summary tool to stop counting procedural steps as cleanup failures.

## MCP Tooling Lessons

The pass confirmed several MCP gaps:

- Need a safe `set_recipe_ingredients` or row-level ingredient repair tool.
- Need an ingredient gap report that includes current row fields, not only display text and missing fields.
- Need cleanup summary to classify procedural unlinked steps separately.
- Need organizer cleanup helpers for orphaned/empty category/tag/tool records.
- Need a better workflow for cocktail/drink recipes, where imported ingredient rows often lack food/unit structure.
