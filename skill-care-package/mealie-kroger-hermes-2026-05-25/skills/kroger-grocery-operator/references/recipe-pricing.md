# Recipe Pricing

## Purpose

Recipe pricing is an estimate of grocery cost consumed by the recipe, not the full cart cost. It is useful for comparing recipes and understanding rough meal cost.

## Process

1. Fetch the Mealie recipe with structured ingredients.
2. For each ingredient, search Kroger at store `03500445`.
3. Pick a normal product candidate.
4. Record product price and package size.
5. Convert the recipe amount into the product basis.
6. Prorate the product price to the recipe amount.
7. Sum ingredient costs.
8. Add a timestamped price block to the recipe description.
9. Refetch the recipe and verify the block displays cleanly.

## Description Format

Append below existing description text:

```md
---
Price (Kroger, YYYY-MM-DD)

- Total cost: $12.08
- Ingredient costs:
  - Chicken thighs $7.49
  - Cornstarch $0.25
  - Vegetable oil $0.11
```

Keep the block simple and readable. Do not bury the recipe description in product URLs, UPCs, or search diagnostics.

## Assumptions

Use transparent assumptions for hard conversions:

- `1 medium lime` is usually one count item.
- `1 bunch cilantro` can be a package/bunch price.
- small quantities of spices can be very low prorated values if the package is large.
- water should be `$0.00`.

For ambiguous ranges, follow the same recipe-cleanup intuition:

- spicy/intense ingredients often use the low end,
- base ingredients use a practical amount or midpoint,
- note the assumption if it meaningfully changes cost.
