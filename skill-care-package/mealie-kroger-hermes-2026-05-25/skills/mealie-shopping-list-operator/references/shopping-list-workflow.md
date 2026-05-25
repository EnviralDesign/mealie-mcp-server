# Shopping List Workflow

## Find The Target List

Call `get_shopping_lists`. If the user does not specify a list:

- prefer a list named `Shop`,
- prefer a list updated today,
- inspect full contents with `get_shopping_list` before choosing if multiple lists look plausible.

## Before Adding

Inspect existing `listItems`:

- `display`,
- `food.name`,
- `note`,
- `label.name`,
- `checked`.

Avoid adding duplicate unchecked items. If an existing item is note-only but should now be structured, update it instead of adding another line.

## Add Items

Use `add_shopping_items_bulk` for many items when the payload is clear. Use `add_shopping_item` for a single simple note-only item.

For structured items, include:

- `shoppingListId`,
- `quantity` when known,
- `foodId` and a minimal `food` object when supported,
- `labelId`,
- `note` for qualifiers.

For note-only items, include:

- `shoppingListId`,
- `quantity` if useful,
- `note`,
- `labelId` when a category is obvious.

## After Adding

Refetch the list. Verify:

- no unexpected duplicates,
- canonical food is linked where intended,
- generic items remained note-only,
- labels are sensible,
- existing checked items were not reopened.

If Mealie display is awkward because of plural metadata, update the food metadata rather than changing the list note.
