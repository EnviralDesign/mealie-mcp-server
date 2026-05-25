# Ingredient Decisions

## Food

Select the canonical grocery item. Do not make separate foods for every modifier.

Good canonical choices:

- `ginger` with note `fresh, chopped`
- `bell pepper` with note `orange`
- `vegetable oil` with note `(cooking oil)`
- `white onion` with note `large, coarsely chopped`

Create separate foods when shopping behavior differs:

- `fresh basil` versus `dried basil`
- `whole wheat spaghetti` versus generic pasta when the recipe genuinely needs it
- `2% milk`, `almond milk`, `whole bean coffee`

Avoid overfit foods when a note is better:

- use `beer` with note `Leinenkugel's for today`
- use `cereal` with note `not 100% garbage (contains fiber and/or protein)`

## Quantity

Convert fractions to decimals. For ranges:

- spicy/intense items: usually low end,
- base/filling items: midpoint or practical amount,
- optional garnish: zero/blank quantity with note when appropriate.

Use original/source text when structured rows disagree.

## Unit

Resolve existing units first. Create or repair units when display quality matters. Unit metadata should include singular/plural display where useful, e.g. `dash` / `dashes`.

## Notes

Use notes for details that help cooking or shopping but are not the canonical food:

- prep: `fresh, chopped`, `peeled`, `thinly sliced`
- quality/form: `boneless, skinless`, `large`, `low sodium`
- alternate names: `(Korean chili paste)` when helpful
- acceptable alternatives: `or sour cream`

Do not hide essential grocery distinctions in notes when they materially affect shopping.

## Aliases

Add aliases only for genuine alternate names or common misspellings that should resolve to the same food. Do not add every descriptive phrase as an alias.

