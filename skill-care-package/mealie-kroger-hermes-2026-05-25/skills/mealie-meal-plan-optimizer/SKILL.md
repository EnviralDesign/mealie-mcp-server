---
name: mealie-meal-plan-optimizer
description: Draft weekly meal plans from Mealie recipes using recipe prices, ingredient overlap, pantry availability, waste risk, effort, and variety constraints. Use when Codex or Hermes needs to compare random versus curated meal plans, choose recipes that share grocery purchases, estimate shopping trip cost, or prepare a practical dinner plan from the Mealie corpus.
---

# Mealie Meal Plan Optimizer

This is an agentic planning skill. It should help with arithmetic, comparisons, and candidate generation, but the final meal plan still needs judgment.

## Core Loop

1. Define the planning window and constraints: number of dinners, protein preferences, leftovers, schedule, repeats, avoid list, pantry availability, and budget.
2. Pull candidate Mealie recipes with ingredients, servings, tags, tools, and price blocks where available.
3. Normalize ingredients into grocery buckets.
4. Estimate plan cost by combining known recipe price data with Kroger spot checks when needed.
5. Score overlap and waste risk.
6. Produce a practical plan, not only the mathematically cheapest plan.
7. Explain tradeoffs and list shared grocery purchases.

## Optimization Priorities

Use these priorities in order unless the user says otherwise:

1. Eat meals the household actually wants.
2. Avoid wasted perishables.
3. Reuse expensive or short-lived ingredients.
4. Keep shopping simple.
5. Keep weeknight effort realistic.
6. Lower total cart cost.
7. Preserve variety.

Price alone is not enough. A cheaper plan with five unrelated cuisines can cost more at checkout because it forces many one-off ingredients.

## Overlap Heuristics

High-value overlap:

- proteins: chicken thighs, chicken breast, shrimp, salmon, ground beef
- produce: scallions, cilantro, basil, parsley, limes, lemons, cucumbers, bell peppers
- dairy: feta, mozzarella, Greek yogurt, cream cheese
- starches: jasmine rice, tortillas, noodles, pasta
- sauces/pantry: soy sauce, sesame oil, gochujang, honey, curry paste, coconut milk

Treat overlap as stronger when ingredients are:

- perishable,
- sold in larger packages than one recipe needs,
- expensive,
- annoying to buy for one use,
- shared by two or more meals in the same week.

Treat overlap as weaker when ingredients are cheap shelf-stable pantry staples such as salt, sugar, flour, oil, vinegar, and spices already likely on hand.

## Output Shape

Return:

- selected recipes,
- estimated total shopping trip cost,
- per-recipe cost where known,
- shared ingredients and why they matter,
- one-off ingredients that may be wasteful,
- missing price data,
- suggested prep or shopping notes.

## References

Read as needed:

- `references/meal-plan-workflow.md` for a practical planning process.
- `references/overlap-scoring.md` for overlap and waste heuristics.
- `references/experiment-template.md` for random-vs-curated experiments.
