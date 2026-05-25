# Overlap Scoring

## Strong Positive Signals

Give strong overlap credit when multiple recipes share:

- the same main protein,
- the same fresh herb,
- the same short-lived produce,
- the same specialty sauce,
- the same cheese or dairy product,
- the same starch sold in multi-serving packages.

## Weak Positive Signals

Give weaker credit for:

- dry spices,
- salt and pepper,
- sugar,
- flour and cornstarch,
- neutral oil,
- common condiments already likely stocked.

## Negative Signals

Penalize:

- many one-off fresh herbs,
- one recipe requiring a specialty sauce no other recipe uses,
- one recipe requiring a large dairy package used only once,
- too many different proteins in one week,
- repeated cuisines or textures if the week becomes monotonous.

## Manual Scoring Shortcut

For a quick human-readable score, use:

- `+3` high-value perishable overlap,
- `+2` expensive protein or dairy overlap,
- `+1` pantry/sauce overlap,
- `-2` one-off perishable,
- `-1` one-off specialty pantry item.

Do not overfit the arithmetic. Use the score to surface tradeoffs, then make a practical choice.
