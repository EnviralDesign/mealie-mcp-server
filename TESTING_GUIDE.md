# Mealie MCP Testing Guide

Last updated: 2026-02-17

This guide is aligned to the currently exposed MCP tools.

Profile note:
- `core` profile exposes lean day-to-day tools.
- `full` profile adds tools/equipment, labels, and category/tag helper lookups.

## Prereqs

1. Configure `.env`:

```bash
MEALIE_URL=http://localhost:9000
MEALIE_API_TOKEN=your_token_here
```

2. Install deps:

```bash
uv sync
```

3. List tools:

```bash
# Full profile (default)
uv run python test_cli.py --list

# Core profile
MEALIE_MCP_PROFILE=core uv run python test_cli.py --list
```

## Fast Smoke Tests (Day-to-Day Flows)

### 1) Recipe browse + detail

```bash
uv run python -c "
import asyncio
from test_cli import call_tool

async def test():
    recipes = await call_tool('get_recipes', page=1, per_page=5)
    assert recipes.get('items'), 'No recipes returned'
    slug = recipes['items'][0]['slug']
    recipe = await call_tool('get_recipe', slug=slug)
    assert recipe.get('name'), 'Recipe missing name'
    print('OK recipe browse/detail')

asyncio.run(test())
"
```

### 2) Shopping list create + add item + list item read

```bash
uv run python -c "
import asyncio
from test_cli import call_tool

async def test():
    shopping_list = await call_tool('create_shopping_list', name='MCP Smoke List')
    list_id = shopping_list['id']

    item = await call_tool(
        'add_shopping_item',
        shopping_list_id=list_id,
        note='Milk',
        quantity=1,
        unit='gallon'
    )

    fetched = await call_tool('get_shopping_item', item_id=item['id'])
    assert fetched.get('note'), 'Shopping item missing note'
    print('OK shopping list/item flow')

asyncio.run(test())
"
```

### 3) Shopping item bulk create

```bash
uv run python -c "
import asyncio
from test_cli import call_tool

async def test():
    shopping_list = await call_tool('create_shopping_list', name='Bulk Item List')
    list_id = shopping_list['id']

    items = [
        {'shoppingListId': list_id, 'note': 'Bananas', 'quantity': 6, 'checked': False},
        {'shoppingListId': list_id, 'note': 'Yogurt', 'quantity': 2, 'checked': False},
    ]
    created = await call_tool('add_shopping_items_bulk', items=items)
    assert created, 'No items returned from bulk create'
    print('OK shopping bulk create')

asyncio.run(test())
"
```

### 4) Add recipe ingredients to shopping list

```bash
uv run python -c "
import asyncio
from test_cli import call_tool

async def test():
    recipes = await call_tool('get_recipes', page=1, per_page=1)
    assert recipes.get('items'), 'Need at least one recipe'

    recipe = await call_tool('get_recipe', slug=recipes['items'][0]['slug'])
    shopping_list = await call_tool('create_shopping_list', name='Recipe Import List')

    result = await call_tool(
        'add_recipe_to_shopping_list',
        list_id=shopping_list['id'],
        recipe_id=recipe['id'],
        scale=1.0
    )

    print('OK add_recipe_to_shopping_list', result)

asyncio.run(test())
"
```

### 5) Category/tag slug + empty lookups (full profile only)

```bash
uv run python -c "
import asyncio
from test_cli import call_tool

async def test():
    cats = await call_tool('get_categories', page=1, per_page=1)
    if cats.get('items'):
        cat_slug = cats['items'][0]['slug']
        by_slug = await call_tool('get_category_by_slug', slug=cat_slug)
        assert by_slug.get('id'), 'category slug lookup failed'
    empty_cats = await call_tool('get_empty_categories')
    assert empty_cats is not None

    tags = await call_tool('get_tags', page=1, per_page=1)
    if tags.get('items'):
        tag_slug = tags['items'][0]['slug']
        by_slug = await call_tool('get_tag_by_slug', slug=tag_slug)
        assert by_slug.get('id'), 'tag slug lookup failed'
    empty_tags = await call_tool('get_empty_tags')
    assert empty_tags is not None

    print('OK organizer lookup helpers')

asyncio.run(test())
"
```

### 6) Ingredient parser (single + batch)

```bash
uv run python -c "
import asyncio
from test_cli import call_tool

async def test():
    one = await call_tool('parse_ingredient', ingredient_text='2 cups flour')
    many = await call_tool('parse_ingredients', ingredients=['1 tsp salt', '3 eggs'])
    assert one, 'parse_ingredient failed'
    assert many, 'parse_ingredients failed'
    print('OK ingredient parser')

asyncio.run(test())
"
```

### 7) Ingredient formalization on a recipe

```bash
uv run python -c "
import asyncio
from test_cli import call_tool

async def test():
    source = 'roasted-garlic-parmesan-fingerling-potatoes'
    dup = await call_tool('duplicate_recipe', slug=source)
    result = await call_tool(
        'formalize_recipe_ingredients',
        slug=dup,
        create_missing_foods=True,
        create_missing_units=False,
        link_ingredients_to_steps=True,
    )
    assert result.get('status') == 'ok', 'formalization failed'
    print('OK ingredient formalization', result)

asyncio.run(test())
"
```

## Tool Coverage Summary

- Recipes: core CRUD + import/scrape/suggest
- Shopping lists: full CRUD + recipe add/remove
- Shopping items: get/add/bulk-add/update/delete
- Organizers:
  categories/tags CRUD in `core`
  category/tag slug+empty + tools CRUD in `full`
- Foods/Units:
  CRUD (+ merge) in both profiles
- Labels:
  `full` profile only
- Parser/Formalization:
  single + batch + recipe ingredient formalization

## Known Gaps

- Recipe bulk actions are in client but not exposed as MCP tools.
- `get_tool_by_slug` exists in client but is not yet exposed as an MCP tool.
- Most image/asset and admin/system endpoints are intentionally deferred.
