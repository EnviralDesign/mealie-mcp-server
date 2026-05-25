# Meal Plan Workflow

## Candidate Collection

Pull recipes from Mealie with:

- name,
- slug/id,
- servings,
- ingredients,
- categories/tags/tools,
- price block if present,
- notes about effort, equipment, and cuisine.

Filter out recipes the user does not want this week.

## Normalize Grocery Buckets

Group ingredient rows by shopper-relevant canonical food:

- `fresh ginger`, `ginger knob`, and `ginger` can be one bucket when they mean the same grocery item.
- `fresh basil` and `dried basil` are separate buckets.
- `chicken thighs` and `chicken breast` are separate unless the plan explicitly allows substitution.
- `rice vinegar` and `white vinegar` are separate.

Ignore overlap for water. Downweight overlap for salt, pepper, oil, and pantry spices.

## Estimate Cost

Use current Mealie price blocks first. If missing:

- do a limited Kroger pricing pass for expensive ingredients,
- reuse prior pricing assumptions for staples,
- label the estimate as partial if important items remain unpriced.

For shopping trip cost, prefer package-aware thinking over sum-of-recipe-prorates. If three recipes use cilantro, the trip may need one bunch, not three prorated bunches.

## Produce The Plan

A useful plan includes:

- the recipe list,
- why those recipes fit together,
- shared ingredients,
- likely one-off purchases,
- estimated cost,
- prep notes,
- risk notes.
