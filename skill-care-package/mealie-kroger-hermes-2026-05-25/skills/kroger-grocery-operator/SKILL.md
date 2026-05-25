---
name: kroger-grocery-operator
description: Use the Kroger MCP/API for grocery product search, store selection, recipe pricing, shopping cart additions, cart tracking, and order-history workflows. Use when Codex or Hermes needs Kroger product candidates, prices, package sizes, availability, preferred-store verification, cart operations, or Kroger-backed pricing for Mealie recipes and shopping lists.
---

# Kroger Grocery Operator

Use Kroger as a live grocery data source. Do not treat it as a general food ontology.

## Store And State

Preferred store:

- Kroger Cooper
- `location_id`: `03500445`
- address: `5330 S Cooper St, Arlington, TX 76017`

Always pass `location_id="03500445"` for pricing/product-search work unless the user explicitly targets another store. Stored preferences can drift or be missing.

Unraid state should persist under `KROGER_TOKEN_DIR`. Preferred store is stored in `kroger_preferences.json`; local cart tracking is stored in `kroger_cart.json`.

## Product Search Rules

- Search one item at a time or in small batches.
- Prefer ordinary mid-range products from the target store.
- Prefer store brand when it is a normal product.
- Avoid strange cheapest matches, huge bulk sizes, irrelevant variants, and sponsored-looking mismatches.
- Use regular price when both regular and sale price are visible unless the task asks for current sale behavior.
- Verify package size before prorating.
- If Kroger does not return a reliable match, say so and either use a visible proxy or leave it unpriced.

## Cart Safety

Cart tools can add to the actual Kroger cart. Use them only when the user asks to add items or clearly approves.

Kroger public API cart behavior is one-way here:

- adding can affect the actual Kroger cart,
- local remove/clear tools only affect local MCP tracking,
- the user must remove items from the real Kroger cart in the Kroger app/site.

Before bulk cart additions, present the candidate products and quantities if there is ambiguity.

## References

Read as needed:

- `references/product-search.md` for product search and package judgment.
- `references/recipe-pricing.md` for Kroger-backed recipe pricing.
- `references/cart-and-state.md` for cart safety, auth, and persistent state.
