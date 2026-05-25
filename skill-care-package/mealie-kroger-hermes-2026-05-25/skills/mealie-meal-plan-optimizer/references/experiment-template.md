# Random Versus Curated Experiment

Use this when testing whether optimization is worth automating.

## Random Plans

1. Select eligible recipes.
2. Randomly generate five plans.
3. Price each plan with current recipe price blocks where available.
4. List obvious overlap and waste issues.

## Curated Plans

1. Seed around one or two high-value ingredients.
2. Pick recipes with shared perishables and compatible proteins.
3. Keep cuisine and texture variety reasonable.
4. Estimate shopping-trip cost, not only prorated recipe cost.
5. Compare against random plans.

## Output

Return a compact comparison:

```text
Random plan average: $X
Best random: $Y
Curated plan average: $Z
Best curated: $W

Main difference:
- curated plans reused cilantro, tortillas, and chicken thighs
- random plans created more one-off produce and sauce purchases
```

Then recommend whether a lightweight tool would be worth building.
