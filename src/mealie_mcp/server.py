"""
Mealie MCP Server - Main server definition.

This is the entry point for the MCP server. It registers all tools
and handles the MCP protocol communication.

Tool Profiles:
- core: recipe/shopping/food/unit/category/tag/parser workflows (leaner toolset)
- full: everything in core, plus tools/equipment, labels, and category/tag helper lookups

Implemented capabilities across profiles:
- Recipe CRUD (get, create, update, patch, delete, duplicate)
- Recipe Import (from URL, test scrape)
- Shopping Lists CRUD + recipe integration
- Shopping Items (read + CRUD + bulk create)
- Categories CRUD
- Tags CRUD
- Foods CRUD + merge
- Units CRUD + merge
- Ingredient parsing (single + batch)
"""

import os
import re
import uuid

from fastmcp import FastMCP

from mealie_mcp.client import get_client

# Supported profiles:
# - core: day-to-day recipe/shopping/ingredient workflows
# - full: complete tool surface in this repository
PROFILE = os.getenv("MEALIE_MCP_PROFILE", "full").lower()
if PROFILE not in {"core", "full"}:
    PROFILE = "full"


def register_tool(*profiles: str):
    """Register a tool only for the specified profile(s)."""
    def decorator(fn):
        if PROFILE in profiles:
            return mcp.tool()(fn)
        return fn
    return decorator


# Initialize the MCP server
mcp = FastMCP(
    name="mealie",
    instructions="""
    You are connected to a Mealie recipe management server.
    
    You can help users:
    - Search, view, create, update, and delete recipes
    - Import recipes from URLs
    - Manage shopping lists and add recipe ingredients
    - Organize recipes with categories, tags, and tools
    - Manage the food and unit databases
    - Parse ingredient text into structured data
    
    When working with recipes, prefer using slugs over IDs when possible.
    For categories, tags, tools, foods, units, and labels - use IDs.
    """,
)


def _normalize_name(value: str | None) -> str:
    """Normalize a human-facing name for exact-ish matching."""
    return re.sub(r"\s+", " ", value or "").strip().lower()


def _items_from_page(page: dict | list | None) -> list[dict]:
    if isinstance(page, dict):
        items = page.get("items", [])
        return items if isinstance(items, list) else []
    if isinstance(page, list):
        return page
    return []


def _find_by_name(items: list[dict], name: str) -> dict | None:
    key = _normalize_name(name)
    for item in items:
        if _normalize_name(item.get("name")) == key:
            return item
    return None


def _entity_ref(item: dict) -> dict:
    """Return the compact organizer shape accepted by recipe patch endpoints."""
    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "slug": item.get("slug"),
        "groupId": item.get("groupId"),
    }


def _coerce_food_aliases(aliases: list[str | dict] | None) -> list[dict]:
    result = []
    for alias in aliases or []:
        if isinstance(alias, str):
            name = alias.strip()
            if name:
                result.append({"name": name})
        elif isinstance(alias, dict):
            name = (alias.get("name") or "").strip()
            if name:
                merged = dict(alias)
                merged["name"] = name
                result.append(merged)
    return result


def _merge_food_aliases(existing: list[dict] | None, additions: list[dict]) -> list[dict]:
    merged: dict[str, dict] = {}
    for alias in existing or []:
        if not isinstance(alias, dict):
            continue
        name = (alias.get("name") or "").strip()
        if name:
            merged[_normalize_name(name)] = alias
    for alias in additions:
        name = (alias.get("name") or "").strip()
        if name:
            merged[_normalize_name(name)] = alias
    return list(merged.values())


async def _resolve_label_id(
    client,
    *,
    label_id: str | None = None,
    label_name: str | None = None,
    create_missing_label: bool = False,
    label_color: str = "#E0E0E0",
) -> str | None:
    if label_id:
        return label_id
    if not label_name or not label_name.strip():
        return None

    clean = label_name.strip()
    page = await client.get_labels(page=1, per_page=50, search=clean)
    label = _find_by_name(_items_from_page(page), clean)
    if label and label.get("id"):
        return label["id"]
    if create_missing_label:
        created = await client.create_label(clean, label_color)
        return created.get("id")
    raise ValueError(f"Label not found: {clean}")


async def _apply_food_metadata(
    client,
    food: dict,
    *,
    name: str | None = None,
    plural_name: str | None = None,
    description: str | None = None,
    label_id: str | None = None,
    label_name: str | None = None,
    aliases: list[str | dict] | None = None,
    merge_aliases: bool = True,
    create_missing_label: bool = False,
    label_color: str = "#E0E0E0",
    only_fill_blanks: bool = False,
) -> dict:
    data = dict(food)
    changed = False

    field_updates = {
        "name": name,
        "pluralName": plural_name,
        "description": description,
    }
    for field, value in field_updates.items():
        if value is None:
            continue
        if only_fill_blanks and data.get(field):
            continue
        if data.get(field) != value:
            data[field] = value
            changed = True

    resolved_label_id = await _resolve_label_id(
        client,
        label_id=label_id,
        label_name=label_name,
        create_missing_label=create_missing_label,
        label_color=label_color,
    )
    if resolved_label_id and (not only_fill_blanks or not data.get("labelId")):
        if data.get("labelId") != resolved_label_id:
            data["labelId"] = resolved_label_id
            changed = True

    new_aliases = _coerce_food_aliases(aliases)
    if aliases is not None:
        final_aliases = (
            _merge_food_aliases(data.get("aliases"), new_aliases)
            if merge_aliases
            else new_aliases
        )
        if data.get("aliases") != final_aliases:
            data["aliases"] = final_aliases
            changed = True

    if not changed:
        return food

    return await client.update_food(data["id"], data)


async def _resolve_organizers(
    client,
    *,
    kind: str,
    ids: list[str] | None,
    names: list[str] | None,
    create_missing: bool,
) -> tuple[list[dict], list[str]]:
    if kind == "category":
        get_one = client.get_category
        list_many = client.get_categories
        create_one = client.create_category
    elif kind == "tag":
        get_one = client.get_tag
        list_many = client.get_tags
        create_one = client.create_tag
    elif kind == "tool":
        get_one = client.get_tool
        list_many = client.get_tools
        create_one = client.create_tool
    else:
        raise ValueError(f"Unsupported organizer kind: {kind}")

    selected: dict[str, dict] = {}
    missing: list[str] = []

    for item_id in ids or []:
        if not item_id:
            continue
        item = await get_one(item_id)
        if item.get("id"):
            selected[item["id"]] = _entity_ref(item)

    for raw_name in names or []:
        if not isinstance(raw_name, str) or not raw_name.strip():
            continue
        clean = raw_name.strip()
        page = await list_many(page=1, per_page=50, search=clean)
        item = _find_by_name(_items_from_page(page), clean)
        if not item and create_missing:
            item = await create_one(clean)
        if item and item.get("id"):
            selected[item["id"]] = _entity_ref(item)
        else:
            missing.append(clean)

    return list(selected.values()), missing


async def _resolve_food(
    client,
    *,
    food_id: str | None = None,
    food_name: str | None = None,
    create_missing_food: bool = False,
    food_description: str = "",
) -> dict | None:
    if food_id:
        return await client.get_food(food_id)
    if not food_name or not food_name.strip():
        return None

    clean = food_name.strip()
    page = await client.get_foods(page=1, per_page=50, search=clean)
    food = _find_by_name(_items_from_page(page), clean)
    if food:
        return food
    if create_missing_food:
        return await client.create_food(clean, description=food_description)
    raise ValueError(f"Food not found: {clean}")


async def _resolve_unit(
    client,
    *,
    unit_id: str | None = None,
    unit_name: str | None = None,
    create_missing_unit: bool = False,
    unit_abbreviation: str = "",
) -> dict | None:
    if unit_id:
        return await client.get_unit(unit_id)
    if not unit_name or not unit_name.strip():
        return None

    clean = unit_name.strip()
    page = await client.get_units(page=1, per_page=250)
    clean_key = _normalize_name(clean)
    for unit in _items_from_page(page):
        names = [
            unit.get("name"),
            unit.get("pluralName"),
            unit.get("abbreviation"),
            unit.get("pluralAbbreviation"),
        ]
        if any(_normalize_name(name) == clean_key for name in names if name):
            return unit
    if create_missing_unit:
        return await client.create_unit(clean, abbreviation=unit_abbreviation, fraction=True)
    raise ValueError(f"Unit not found: {clean}")


def _ingredient_reference_lookup(recipe: dict) -> tuple[dict[str, list[str]], set[str]]:
    lookup: dict[str, list[str]] = {}
    all_reference_ids: set[str] = set()

    for ingredient in recipe.get("recipeIngredient", []) or []:
        ref_id = ingredient.get("referenceId")
        if not ref_id:
            continue
        all_reference_ids.add(ref_id)

        food = ingredient.get("food") if isinstance(ingredient.get("food"), dict) else {}
        tokens = [
            food.get("name") if food else None,
            ingredient.get("note"),
            ingredient.get("display"),
            ingredient.get("originalText"),
        ]
        for token in tokens:
            key = _normalize_name(token)
            if key:
                lookup.setdefault(key, []).append(ref_id)

    return lookup, all_reference_ids


def _resolve_ingredient_names(
    lookup: dict[str, list[str]],
    names: list[str],
) -> tuple[list[str], list[str], list[str]]:
    resolved: list[str] = []
    missing: list[str] = []
    ambiguous: list[str] = []

    for raw_name in names:
        if not isinstance(raw_name, str) or not raw_name.strip():
            continue
        clean = raw_name.strip()
        key = _normalize_name(clean)

        matches = lookup.get(key, [])
        if not matches and len(key) >= 4:
            candidate_ids: list[str] = []
            for token, ids in lookup.items():
                if key in token or token in key:
                    candidate_ids.extend(ids)
            matches = candidate_ids

        unique_matches = list(dict.fromkeys(matches))
        if len(unique_matches) == 1:
            resolved.extend(unique_matches)
        elif len(unique_matches) > 1:
            ambiguous.append(clean)
        else:
            missing.append(clean)

    return resolved, missing, ambiguous


def _matching_ingredient_reference_ids(lookup: dict[str, list[str]], name: str) -> list[str]:
    key = _normalize_name(name)
    matches = lookup.get(key, [])
    if not matches and len(key) >= 4:
        for token, ids in lookup.items():
            if key in token or token in key:
                matches.extend(ids)
    return list(dict.fromkeys(matches))


def _text_mentions_quantity(text: str | None) -> bool:
    return bool(re.search(r"\b\d+([./-]\d+)?\b", text or ""))


def _text_starts_with_measured_unit(text: str | None) -> bool:
    unit_pattern = (
        r"("
        r"teaspoons?|tablespoons?|tbsp|tsp|cups?|ounces?|oz|pounds?|lbs?|grams?|g|"
        r"kilograms?|kg|milliliters?|ml|liters?|l|pinches?|dashes?|cloves?|bunches?|"
        r"cans?|jars?|packages?|packs?|slices?|sticks?|sprigs?"
        r")"
    )
    quantity_pattern = r"(\d+([./-]\d+)?|\d+\s+\d+/\d+|[¼½¾⅓⅔⅛⅜⅝⅞¹²³⁄₀₁₂₃₄₅₆₇₈₉]+)"
    pattern = rf"^\s*{quantity_pattern}\s+{unit_pattern}\b"
    return bool(re.search(pattern, text or "", flags=re.IGNORECASE))


# =============================================================================
# Recipe Tools - Core CRUD
# =============================================================================

@register_tool("core", "full")
async def get_recipes(
    search: str | None = None,
    page: int = 1,
    per_page: int = 20,
) -> dict:
    """Get a list of recipes. Use search to filter by name/description."""
    client = get_client()
    return await client.get_recipes(page=page, per_page=min(per_page, 50), search=search)


@register_tool("core", "full")
async def get_recipe(slug: str) -> dict:
    """Get complete details for a recipe including ingredients and instructions."""
    client = get_client()
    return await client.get_recipe(slug)


@register_tool("core", "full")
async def create_recipe(name: str, description: str = "") -> str:
    """Create a new empty recipe. Returns the slug."""
    client = get_client()
    return await client.create_recipe({"name": name, "description": description})


@register_tool("core", "full")
async def update_recipe(slug: str, recipe_data: dict) -> dict:
    """
    Full update of a recipe. Requires complete recipe data.
    
    Args:
        slug: Recipe slug to update
        recipe_data: Complete recipe object with all fields
    """
    client = get_client()
    return await client.update_recipe(slug, recipe_data)


@register_tool("core", "full")
async def patch_recipe(slug: str, updates: dict) -> dict:
    """
    Partial update of a recipe. Only updates provided fields.
    
    Args:
        slug: Recipe slug to update
        updates: Dictionary of fields to update (e.g., {"description": "New desc"})
    """
    client = get_client()
    return await client.patch_recipe(slug, updates)


@register_tool("core", "full")
async def delete_recipe(slug: str) -> dict:
    """Delete a recipe by slug."""
    client = get_client()
    await client.delete_recipe(slug)
    return {"status": "deleted", "slug": slug}


@register_tool("core", "full")
async def duplicate_recipe(slug: str) -> str:
    """Duplicate a recipe. Returns the new recipe's slug."""
    client = get_client()
    return await client.duplicate_recipe(slug)


@register_tool("core", "full")
async def set_recipe_last_made(slug: str, date: str) -> dict:
    """Set when a recipe was last made. Date format: YYYY-MM-DD"""
    client = get_client()
    return await client.set_recipe_last_made(slug, date)


# =============================================================================
# Recipe Tools - Import & Scraping
# =============================================================================

@register_tool("core", "full")
async def import_recipe_from_url(url: str, include_tags: bool = False) -> str:
    """Import a recipe from a website URL. Returns the slug of the created recipe."""
    client = get_client()
    return await client.import_recipe_from_url(url, include_tags=include_tags)


@register_tool("core", "full")
async def import_or_get_recipe_from_url(
    url: str,
    include_tags: bool = False,
    dedupe_by_org_url: bool = True,
    import_as_name: str | None = None,
) -> dict:
    """
    Import a recipe from URL, or return an existing recipe when orgURL already matches.

    Returns:
      {"status":"existing","slug":"..."} or {"status":"imported","slug":"..."}
    """
    client = get_client()
    normalized = url.strip()

    if dedupe_by_org_url:
        page = 1
        while True:
            batch = await client.get_recipes(page=page, per_page=50)
            items = batch.get("items", [])
            if not items:
                break

            for item in items:
                slug = item.get("slug")
                if not slug:
                    continue
                try:
                    recipe = await client.get_recipe(slug)
                except Exception:
                    continue
                org_url = (recipe.get("orgURL") or "").strip()
                if org_url and org_url == normalized:
                    return {"status": "existing", "slug": slug}

            if len(items) < 50:
                break
            page += 1

    slug = await client.import_recipe_from_url(normalized, include_tags=include_tags)
    if import_as_name:
        await client.patch_recipe(slug, {"name": import_as_name})
    return {"status": "imported", "slug": slug}


@register_tool("core", "full")
async def test_scrape_url(url: str) -> dict:
    """Test scraping a recipe URL without saving. Useful to preview before import."""
    client = get_client()
    return await client.test_scrape_url(url)


@register_tool("core", "full")
async def suggest_recipes() -> dict:
    """Get recipe suggestions based on mealplan rules."""
    client = get_client()
    return await client.get_recipe_suggestions()


# =============================================================================
# Recipe Tools - Bulk Actions
# =============================================================================

# =============================================================================
# Shopping List Tools
# =============================================================================

@register_tool("core", "full")
async def get_shopping_lists(page: int = 1, per_page: int = 20) -> dict:
    """Get all shopping lists."""
    client = get_client()
    return await client.get_shopping_lists(page=page, per_page=per_page)


@register_tool("core", "full")
async def get_shopping_list(list_id: str) -> dict:
    """Get a shopping list with all its items."""
    client = get_client()
    return await client.get_shopping_list(list_id)


@register_tool("core", "full")
async def create_shopping_list(name: str) -> dict:
    """Create a new shopping list."""
    client = get_client()
    return await client.create_shopping_list(name)


@register_tool("core", "full")
async def update_shopping_list(list_id: str, name: str) -> dict:
    """Update a shopping list's name."""
    client = get_client()
    current = await client.get_shopping_list(list_id)
    current["name"] = name
    return await client.update_shopping_list(list_id, current)


@register_tool("core", "full")
async def delete_shopping_list(list_id: str) -> dict:
    """Delete a shopping list."""
    client = get_client()
    await client.delete_shopping_list(list_id)
    return {"status": "deleted", "id": list_id}


@register_tool("core", "full")
async def add_recipe_to_shopping_list(list_id: str, recipe_id: str, scale: float = 1.0) -> dict:
    """Add all ingredients from a recipe to a shopping list."""
    client = get_client()
    return await client.add_recipe_to_shopping_list(list_id, recipe_id, scale)


@register_tool("core", "full")
async def remove_recipe_from_shopping_list(list_id: str, recipe_id: str) -> dict:
    """Remove a recipe's ingredients from a shopping list."""
    client = get_client()
    return await client.remove_recipe_from_shopping_list(list_id, recipe_id)


# =============================================================================
# Shopping Item Tools
# =============================================================================

@register_tool("core", "full")
async def get_shopping_items(page: int = 1, per_page: int = 50) -> dict:
    """Get all shopping items across lists."""
    client = get_client()
    return await client.get_shopping_items(page=page, per_page=per_page)


@register_tool("core", "full")
async def get_shopping_item(item_id: str) -> dict:
    """Get a specific shopping item by ID."""
    client = get_client()
    return await client.get_shopping_item(item_id)


@register_tool("core", "full")
async def add_shopping_item(
    shopping_list_id: str,
    note: str,
    quantity: float = 1,
    unit: str | None = None,
    checked: bool = False,
) -> dict:
    """Add an item to a shopping list."""
    client = get_client()
    result = await client.add_shopping_item(
        shopping_list_id=shopping_list_id,
        note=note,
        quantity=quantity,
        unit=unit,
        checked=checked,
    )
    # Mealie returns a change-set wrapper; return the created item when possible.
    if isinstance(result, dict) and isinstance(result.get("createdItems"), list) and len(result["createdItems"]) == 1:
        return result["createdItems"][0]
    return result


@register_tool("core", "full")
async def add_shopping_items_bulk(items: list[dict]) -> list[dict]:
    """Add multiple shopping items in one request."""
    client = get_client()
    result = await client.add_shopping_items_bulk(items)
    # Normalize change-set style response to the created item list.
    if isinstance(result, dict) and isinstance(result.get("createdItems"), list):
        return result["createdItems"]
    return result


@register_tool("core", "full")
async def update_shopping_item(item_id: str, checked: bool | None = None, note: str | None = None) -> dict:
    """Update a shopping item (mark as checked, change note, etc.)."""
    client = get_client()
    data = await client.get_shopping_item(item_id)
    if checked is not None:
        data["checked"] = checked
    if note is not None:
        data["note"] = note
    return await client.update_shopping_item(item_id, data)


@register_tool("core", "full")
async def delete_shopping_item(item_id: str) -> dict:
    """Delete a shopping item."""
    client = get_client()
    await client.delete_shopping_item(item_id)
    return {"status": "deleted", "id": item_id}


# =============================================================================
# Category Tools
# =============================================================================

@register_tool("core", "full")
async def get_categories(search: str | None = None, page: int = 1, per_page: int = 50) -> dict:
    """Get recipe categories. Use search to filter by name."""
    client = get_client()
    return await client.get_categories(page=page, per_page=per_page, search=search)


@register_tool("core", "full")
async def get_category(category_id: str) -> dict:
    """Get a specific category by ID."""
    client = get_client()
    return await client.get_category(category_id)


@register_tool("full")
async def get_category_by_slug(slug: str) -> dict:
    """Get a category by slug."""
    client = get_client()
    return await client.get_category_by_slug(slug)


@register_tool("full")
async def get_empty_categories() -> dict:
    """Get categories that currently have no recipes."""
    client = get_client()
    return await client.get_empty_categories()


@register_tool("core", "full")
async def create_category(name: str) -> dict:
    """Create a new recipe category."""
    client = get_client()
    return await client.create_category(name)


@register_tool("core", "full")
async def update_category(category_id: str, name: str) -> dict:
    """Update a category's name."""
    client = get_client()
    return await client.update_category(category_id, {"name": name})


@register_tool("core", "full")
async def delete_category(category_id: str) -> dict:
    """Delete a category."""
    client = get_client()
    await client.delete_category(category_id)
    return {"status": "deleted", "id": category_id}


# =============================================================================
# Tag Tools
# =============================================================================

@register_tool("core", "full")
async def get_tags(search: str | None = None, page: int = 1, per_page: int = 50) -> dict:
    """Get recipe tags. Use search to filter by name."""
    client = get_client()
    return await client.get_tags(page=page, per_page=per_page, search=search)


@register_tool("core", "full")
async def get_tag(tag_id: str) -> dict:
    """Get a specific tag by ID."""
    client = get_client()
    return await client.get_tag(tag_id)


@register_tool("full")
async def get_tag_by_slug(slug: str) -> dict:
    """Get a tag by slug."""
    client = get_client()
    return await client.get_tag_by_slug(slug)


@register_tool("full")
async def get_empty_tags() -> dict:
    """Get tags that currently have no recipes."""
    client = get_client()
    return await client.get_empty_tags()


@register_tool("core", "full")
async def create_tag(name: str) -> dict:
    """Create a new recipe tag."""
    client = get_client()
    return await client.create_tag(name)


@register_tool("core", "full")
async def update_tag(tag_id: str, name: str) -> dict:
    """Update a tag's name."""
    client = get_client()
    return await client.update_tag(tag_id, {"name": name})


@register_tool("core", "full")
async def delete_tag(tag_id: str) -> dict:
    """Delete a tag."""
    client = get_client()
    await client.delete_tag(tag_id)
    return {"status": "deleted", "id": tag_id}


# =============================================================================
# Tool (Kitchen Equipment) Tools
# =============================================================================

@register_tool("core", "full")
async def get_tools(search: str | None = None, page: int = 1, per_page: int = 50) -> dict:
    """Get kitchen tools/equipment. Use search to filter by name."""
    client = get_client()
    return await client.get_tools(page=page, per_page=per_page, search=search)


@register_tool("core", "full")
async def get_tool(tool_id: str) -> dict:
    """Get a specific tool by ID."""
    client = get_client()
    return await client.get_tool(tool_id)


@register_tool("full")
async def get_tool_by_slug(slug: str) -> dict:
    """Get a kitchen tool by slug."""
    client = get_client()
    return await client.get_tool_by_slug(slug)


@register_tool("core", "full")
async def create_tool(name: str) -> dict:
    """Create a new kitchen tool."""
    client = get_client()
    return await client.create_tool(name)


@register_tool("core", "full")
async def update_tool(tool_id: str, name: str) -> dict:
    """Update a tool's name."""
    client = get_client()
    return await client.update_tool(tool_id, {"name": name})


@register_tool("core", "full")
async def delete_tool(tool_id: str) -> dict:
    """Delete a tool."""
    client = get_client()
    await client.delete_tool(tool_id)
    return {"status": "deleted", "id": tool_id}


@register_tool("core", "full")
async def set_recipe_tools(
    slug: str,
    tool_ids: list[str] | None = None,
    tool_names: list[str] | None = None,
    create_missing_tools: bool = False,
) -> dict:
    """
    Set recipe tools using IDs and/or names while handling Mealie's full-tool-object requirement.
    """
    client = get_client()
    selected: dict[str, dict] = {}

    for tool_id in tool_ids or []:
        tool = await client.get_tool(tool_id)
        tid = tool.get("id")
        if tid:
            selected[tid] = {
                "id": tool.get("id"),
                "name": tool.get("name"),
                "slug": tool.get("slug"),
                "groupId": tool.get("groupId"),
            }

    if tool_names:
        tools_page = await client.get_tools(page=1, per_page=250)
        by_name = {
            (t.get("name") or "").strip().lower(): t
            for t in tools_page.get("items", [])
            if (t.get("name") or "").strip()
        }
        for raw_name in tool_names:
            if not isinstance(raw_name, str) or not raw_name.strip():
                continue
            key = raw_name.strip().lower()
            tool = by_name.get(key)
            if not tool and create_missing_tools:
                tool = await client.create_tool(raw_name.strip())
                by_name[key] = tool
            if tool and tool.get("id"):
                tid = tool["id"]
                selected[tid] = {
                    "id": tool.get("id"),
                    "name": tool.get("name"),
                    "slug": tool.get("slug"),
                    "groupId": tool.get("groupId"),
                }

    await client.patch_recipe(slug, {"tools": list(selected.values())})
    return {"status": "ok", "slug": slug, "tool_count": len(selected)}


@register_tool("core", "full")
async def set_recipe_organizers(
    slug: str,
    category_ids: list[str] | None = None,
    category_names: list[str] | None = None,
    tag_ids: list[str] | None = None,
    tag_names: list[str] | None = None,
    tool_ids: list[str] | None = None,
    tool_names: list[str] | None = None,
    create_missing: bool = False,
) -> dict:
    """
    Set recipe categories, tags, and required tools by ID and/or exact name.

    This replaces only the organizer groups provided. Name lookups use Mealie's
    partial search plus an exact normalized match before optional creation.
    """
    client = get_client()
    patch: dict = {}
    missing: dict[str, list[str]] = {}
    counts: dict[str, int] = {}

    if category_ids is not None or category_names is not None:
        categories, missing_categories = await _resolve_organizers(
            client,
            kind="category",
            ids=category_ids,
            names=category_names,
            create_missing=create_missing,
        )
        patch["recipeCategory"] = categories
        missing["categories"] = missing_categories
        counts["categories"] = len(categories)

    if tag_ids is not None or tag_names is not None:
        tags, missing_tags = await _resolve_organizers(
            client,
            kind="tag",
            ids=tag_ids,
            names=tag_names,
            create_missing=create_missing,
        )
        patch["tags"] = tags
        missing["tags"] = missing_tags
        counts["tags"] = len(tags)

    if tool_ids is not None or tool_names is not None:
        tools, missing_tools = await _resolve_organizers(
            client,
            kind="tool",
            ids=tool_ids,
            names=tool_names,
            create_missing=create_missing,
        )
        patch["tools"] = tools
        missing["tools"] = missing_tools
        counts["tools"] = len(tools)

    if not patch:
        return {
            "status": "no-op",
            "slug": slug,
            "message": "No categories, tags, or tools were provided.",
        }

    await client.patch_recipe(slug, patch)
    return {
        "status": "ok",
        "slug": slug,
        "counts": counts,
        "missing": {key: value for key, value in missing.items() if value},
    }


@register_tool("core", "full")
async def set_recipe_instructions(
    slug: str,
    steps: list[dict],
    auto_link_by_text: bool = False,
    keep_existing_ids: bool = False,
) -> dict:
    """
    Replace recipe instructions with structured, scan-friendly steps.

    Each step must include text and may include title, summary,
    ingredient_reference_ids, and/or ingredient_names. ingredient_names are
    resolved against the recipe's current structured ingredients.
    """
    if not steps:
        raise ValueError("steps must contain at least one instruction")

    client = get_client()
    recipe = await client.get_recipe(slug)
    existing_steps = recipe.get("recipeInstructions") or []
    lookup, all_reference_ids = _ingredient_reference_lookup(recipe)

    updated_steps: list[dict] = []
    missing_names: list[str] = []
    ambiguous_names: list[str] = []
    ambiguous_matches: dict[str, list[str]] = {}
    invalid_reference_ids: list[str] = []

    for index, raw_step in enumerate(steps):
        if not isinstance(raw_step, dict):
            raise ValueError("Each step must be an object with at least a text field")

        text = (raw_step.get("text") or "").strip()
        if not text:
            raise ValueError(f"Step {index + 1} is missing text")

        step_id = raw_step.get("id")
        if not step_id and keep_existing_ids and index < len(existing_steps):
            step_id = existing_steps[index].get("id")
        if not step_id:
            step_id = str(uuid.uuid4())

        reference_ids: list[str] = []
        raw_reference_ids = (
            raw_step.get("ingredient_reference_ids")
            or raw_step.get("ingredientReferenceIds")
            or []
        )
        for ref_id in raw_reference_ids:
            if ref_id in all_reference_ids:
                reference_ids.append(ref_id)
            else:
                invalid_reference_ids.append(str(ref_id))

        raw_reference_objects = raw_step.get("ingredientReferences") or []
        for ref in raw_reference_objects:
            ref_id = ref.get("referenceId") if isinstance(ref, dict) else None
            if ref_id in all_reference_ids:
                reference_ids.append(ref_id)
            elif ref_id:
                invalid_reference_ids.append(str(ref_id))

        ingredient_names = raw_step.get("ingredient_names") or raw_step.get("ingredientNames") or []
        resolved, missing, ambiguous = _resolve_ingredient_names(lookup, ingredient_names)
        reference_ids.extend(resolved)
        missing_names.extend(missing)
        ambiguous_names.extend(ambiguous)
        for name in ambiguous:
            ambiguous_matches[name] = _matching_ingredient_reference_ids(lookup, name)

        if auto_link_by_text:
            text_key = _normalize_name(text)
            for token, ids in lookup.items():
                if len(token) < 4:
                    continue
                words = [w for w in re.split(r"\s+", token) if len(w) >= 4]
                if token in text_key or any(word in text_key for word in words):
                    reference_ids.extend(ids)

        deduped_reference_ids = list(dict.fromkeys(reference_ids))
        updated_steps.append({
            "id": step_id,
            "title": raw_step.get("title") or "",
            "summary": raw_step.get("summary") or "",
            "text": text,
            "ingredientReferences": [
                {"referenceId": ref_id}
                for ref_id in deduped_reference_ids
            ],
        })

    await client.patch_recipe(slug, {"recipeInstructions": updated_steps})
    return {
        "status": "ok",
        "slug": slug,
        "instruction_count": len(updated_steps),
        "linked_steps": sum(1 for step in updated_steps if step["ingredientReferences"]),
        "missing_ingredient_names": list(dict.fromkeys(missing_names)),
        "ambiguous_ingredient_names": list(dict.fromkeys(ambiguous_names)),
        "ambiguous_ingredient_matches": [
            {"name": name, "referenceIds": reference_ids}
            for name, reference_ids in ambiguous_matches.items()
        ],
        "invalid_reference_ids": list(dict.fromkeys(invalid_reference_ids)),
    }


@register_tool("core", "full")
async def get_recipe_ingredient_rows(slug: str) -> dict:
    """
    Return concise ingredient rows for row-level cleanup.

    This is easier to review than the full recipe object when repairing imported
    ingredient rows by referenceId.
    """
    client = get_client()
    recipe = await client.get_recipe(slug)
    rows = []
    for ingredient in recipe.get("recipeIngredient", []) or []:
        food = ingredient.get("food") if isinstance(ingredient.get("food"), dict) else {}
        unit = ingredient.get("unit") if isinstance(ingredient.get("unit"), dict) else {}
        rows.append({
            "referenceId": ingredient.get("referenceId"),
            "quantity": ingredient.get("quantity"),
            "unitId": ingredient.get("unitId") or unit.get("id"),
            "unit": unit.get("name") or unit.get("abbreviation"),
            "foodId": ingredient.get("foodId") or food.get("id"),
            "food": food.get("name"),
            "note": ingredient.get("note"),
            "display": ingredient.get("display"),
            "originalText": ingredient.get("originalText"),
            "title": ingredient.get("title"),
        })
    return {"slug": slug, "ingredient_count": len(rows), "ingredients": rows}


@register_tool("core", "full")
async def update_recipe_ingredient_row(
    slug: str,
    reference_id: str,
    quantity: float | None = None,
    food_id: str | None = None,
    food_name: str | None = None,
    unit_id: str | None = None,
    unit_name: str | None = None,
    note: str | None = None,
    display: str | None = None,
    title: str | None = None,
    original_text: str | None = None,
    create_missing_food: bool = False,
    food_description: str = "",
    create_missing_unit: bool = False,
    unit_abbreviation: str = "",
    clear_unit: bool = False,
    clear_food: bool = False,
) -> dict:
    """
    Update one recipe ingredient row by referenceId while preserving all others.

    Use this for malformed import rows after reviewing the current row with
    get_recipe_ingredient_rows. Food/unit names must resolve exactly unless
    create_missing_food/create_missing_unit is enabled.
    """
    if not reference_id:
        raise ValueError("reference_id is required")
    if clear_food and (food_id or food_name):
        raise ValueError("clear_food cannot be combined with food_id or food_name")
    if clear_unit and (unit_id or unit_name):
        raise ValueError("clear_unit cannot be combined with unit_id or unit_name")

    client = get_client()
    recipe = await client.get_recipe(slug)
    ingredients = recipe.get("recipeIngredient", []) or []
    row_index = None
    for index, ingredient in enumerate(ingredients):
        if ingredient.get("referenceId") == reference_id:
            row_index = index
            break
    if row_index is None:
        raise ValueError(f"Ingredient referenceId not found: {reference_id}")

    row = dict(ingredients[row_index])
    before = dict(row)

    if quantity is not None:
        row["quantity"] = quantity
    if note is not None:
        row["note"] = note
    if display is not None:
        row["display"] = display
    if title is not None:
        row["title"] = title
    if original_text is not None:
        row["originalText"] = original_text

    if clear_food:
        row.pop("foodId", None)
        row["food"] = None
    else:
        food = await _resolve_food(
            client,
            food_id=food_id,
            food_name=food_name,
            create_missing_food=create_missing_food,
            food_description=food_description,
        )
        if food:
            row["foodId"] = food.get("id")
            row["food"] = {
                "id": food.get("id"),
                "name": food.get("name"),
                "pluralName": food.get("pluralName"),
            }

    if clear_unit:
        row.pop("unitId", None)
        row["unit"] = None
    else:
        unit = await _resolve_unit(
            client,
            unit_id=unit_id,
            unit_name=unit_name,
            create_missing_unit=create_missing_unit,
            unit_abbreviation=unit_abbreviation,
        )
        if unit:
            row["unitId"] = unit.get("id")
            row["unit"] = {
                "id": unit.get("id"),
                "name": unit.get("name"),
                "abbreviation": unit.get("abbreviation"),
            }

    updated_ingredients = list(ingredients)
    updated_ingredients[row_index] = row
    await client.patch_recipe(slug, {"recipeIngredient": updated_ingredients})

    return {
        "status": "ok",
        "slug": slug,
        "referenceId": reference_id,
        "before": {
            "quantity": before.get("quantity"),
            "unit": (before.get("unit") or {}).get("name") if isinstance(before.get("unit"), dict) else None,
            "food": (before.get("food") or {}).get("name") if isinstance(before.get("food"), dict) else None,
            "note": before.get("note"),
            "display": before.get("display"),
            "originalText": before.get("originalText"),
        },
        "after": {
            "quantity": row.get("quantity"),
            "unit": (row.get("unit") or {}).get("name") if isinstance(row.get("unit"), dict) else None,
            "food": (row.get("food") or {}).get("name") if isinstance(row.get("food"), dict) else None,
            "note": row.get("note"),
            "display": row.get("display"),
            "originalText": row.get("originalText"),
        },
    }


@register_tool("core", "full")
async def update_recipe_ingredient_rows(slug: str, rows: list[dict]) -> dict:
    """
    Update multiple recipe ingredient rows by referenceId.

    Each row accepts the same fields as update_recipe_ingredient_row, except slug.
    Rows are applied sequentially so the response identifies the exact failing row
    if a food/unit cannot be resolved.
    """
    if not rows:
        raise ValueError("rows must contain at least one update")

    results = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"Row update {index + 1} must be an object")
        try:
            result = await update_recipe_ingredient_row(slug=slug, **row)
            results.append(result)
        except Exception as exc:
            return {
                "status": "partial-failure",
                "slug": slug,
                "updated_count": len(results),
                "failed_index": index,
                "failed_row": row,
                "error": str(exc),
                "results": results,
            }

    return {
        "status": "ok",
        "slug": slug,
        "updated_count": len(results),
        "results": results,
    }


@register_tool("core", "full")
async def add_recipe_ingredient_row(
    slug: str,
    food_id: str | None = None,
    food_name: str | None = None,
    quantity: float = 0,
    unit_id: str | None = None,
    unit_name: str | None = None,
    note: str = "",
    display: str | None = None,
    title: str | None = None,
    original_text: str | None = None,
    reference_id: str | None = None,
    insert_after_reference_id: str | None = None,
    create_missing_food: bool = False,
    food_description: str = "",
    create_missing_unit: bool = False,
    unit_abbreviation: str = "",
) -> dict:
    """
    Append or insert one structured ingredient row.

    Use this when source text combines multiple groceries into one imported row
    and the recipe needs an additional structured ingredient reference.
    """
    if not food_id and not food_name:
        raise ValueError("food_id or food_name is required")

    client = get_client()
    recipe = await client.get_recipe(slug)
    ingredients = list(recipe.get("recipeIngredient", []) or [])

    food = await _resolve_food(
        client,
        food_id=food_id,
        food_name=food_name,
        create_missing_food=create_missing_food,
        food_description=food_description,
    )
    unit = await _resolve_unit(
        client,
        unit_id=unit_id,
        unit_name=unit_name,
        create_missing_unit=create_missing_unit,
        unit_abbreviation=unit_abbreviation,
    )

    row = {
        "quantity": quantity,
        "unit": None,
        "food": {
            "id": food.get("id"),
            "name": food.get("name"),
            "pluralName": food.get("pluralName"),
        },
        "foodId": food.get("id"),
        "referencedRecipe": None,
        "note": note,
        "display": display or "",
        "title": title or "",
        "originalText": original_text,
        "referenceId": reference_id or str(uuid.uuid4()),
    }
    if unit:
        row["unitId"] = unit.get("id")
        row["unit"] = {
            "id": unit.get("id"),
            "name": unit.get("name"),
            "abbreviation": unit.get("abbreviation"),
        }

    insert_index = len(ingredients)
    if insert_after_reference_id:
        for index, ingredient in enumerate(ingredients):
            if ingredient.get("referenceId") == insert_after_reference_id:
                insert_index = index + 1
                break
        else:
            raise ValueError(f"insert_after_reference_id not found: {insert_after_reference_id}")

    ingredients.insert(insert_index, row)
    await client.patch_recipe(slug, {"recipeIngredient": ingredients})
    return {
        "status": "ok",
        "slug": slug,
        "referenceId": row["referenceId"],
        "inserted_index": insert_index,
        "ingredient": {
            "quantity": row.get("quantity"),
            "unit": (row.get("unit") or {}).get("name") if isinstance(row.get("unit"), dict) else None,
            "food": (row.get("food") or {}).get("name") if isinstance(row.get("food"), dict) else None,
            "note": row.get("note"),
            "display": row.get("display"),
        },
    }


@register_tool("core", "full")
async def delete_recipe_ingredient_row(slug: str, reference_id: str) -> dict:
    """
    Delete one recipe ingredient row by referenceId.

    Use this for imported equipment or malformed duplicate rows after confirming
    the source recipe should not have that row as a grocery ingredient.
    """
    if not reference_id:
        raise ValueError("reference_id is required")

    client = get_client()
    recipe = await client.get_recipe(slug)
    ingredients = list(recipe.get("recipeIngredient", []) or [])
    kept = [row for row in ingredients if row.get("referenceId") != reference_id]
    if len(kept) == len(ingredients):
        raise ValueError(f"Ingredient referenceId not found: {reference_id}")

    await client.patch_recipe(slug, {"recipeIngredient": kept})
    return {
        "status": "deleted",
        "slug": slug,
        "referenceId": reference_id,
        "ingredient_count": len(kept),
    }


# =============================================================================
# Food Tools
# =============================================================================

@register_tool("core", "full")
async def get_foods(search: str | None = None, page: int = 1, per_page: int = 50) -> dict:
    """Get foods/ingredients from the database. Optionally search by name."""
    client = get_client()
    return await client.get_foods(page=page, per_page=per_page, search=search)


@register_tool("core", "full")
async def get_food(food_id: str) -> dict:
    """Get a specific food by ID."""
    client = get_client()
    return await client.get_food(food_id)


@register_tool("core", "full")
async def create_food(
    name: str,
    description: str = "",
    plural_name: str | None = None,
    label_id: str | None = None,
    label_name: str | None = None,
    aliases: list[str] | None = None,
    create_missing_label: bool = False,
    label_color: str = "#E0E0E0",
) -> dict:
    """
    Create a new food/ingredient with optional Mealie metadata.

    Use plural_name, label_name/label_id, and aliases when creating canonical foods
    during recipe import cleanup.
    """
    client = get_client()
    resolved_label_id = await _resolve_label_id(
        client,
        label_id=label_id,
        label_name=label_name,
        create_missing_label=create_missing_label,
        label_color=label_color,
    )
    return await client.create_food(
        name,
        description=description,
        plural_name=plural_name,
        label_id=resolved_label_id,
        aliases=aliases,
    )


@register_tool("core", "full")
async def update_food(
    food_id: str,
    name: str | None = None,
    description: str | None = None,
    plural_name: str | None = None,
    label_id: str | None = None,
    label_name: str | None = None,
    aliases: list[str] | None = None,
    merge_aliases: bool = True,
    create_missing_label: bool = False,
    label_color: str = "#E0E0E0",
) -> dict:
    """
    Update a food's canonical metadata.

    aliases are merged with existing aliases by default; set merge_aliases=false
    to replace them.
    """
    client = get_client()
    food = await client.get_food(food_id)
    return await _apply_food_metadata(
        client,
        food,
        name=name,
        plural_name=plural_name,
        description=description,
        label_id=label_id,
        label_name=label_name,
        aliases=aliases,
        merge_aliases=merge_aliases,
        create_missing_label=create_missing_label,
        label_color=label_color,
    )


@register_tool("core", "full")
async def get_or_create_food(
    name: str,
    description: str = "",
    plural_name: str | None = None,
    label_id: str | None = None,
    label_name: str | None = None,
    aliases: list[str] | None = None,
    create_missing_label: bool = False,
    label_color: str = "#E0E0E0",
    enrich_existing: bool = True,
    overwrite_existing_metadata: bool = False,
) -> dict:
    """
    Find a food by exact name, or create it if absent.

    When enrich_existing is true, provided metadata is filled onto an existing
    food. Existing non-empty metadata is preserved unless overwrite_existing_metadata
    is true.
    """
    if not name or not name.strip():
        raise ValueError("name is required")

    client = get_client()
    clean = name.strip()
    page = await client.get_foods(page=1, per_page=50, search=clean)
    food = _find_by_name(_items_from_page(page), clean)

    if food:
        if enrich_existing:
            food = await _apply_food_metadata(
                client,
                food,
                plural_name=plural_name,
                description=description if description else None,
                label_id=label_id,
                label_name=label_name,
                aliases=aliases,
                merge_aliases=True,
                create_missing_label=create_missing_label,
                label_color=label_color,
                only_fill_blanks=not overwrite_existing_metadata,
            )
        return {"status": "existing", "food": food}

    resolved_label_id = await _resolve_label_id(
        client,
        label_id=label_id,
        label_name=label_name,
        create_missing_label=create_missing_label,
        label_color=label_color,
    )
    food = await client.create_food(
        clean,
        description=description,
        plural_name=plural_name,
        label_id=resolved_label_id,
        aliases=aliases,
    )
    return {"status": "created", "food": food}


@register_tool("core", "full")
async def delete_food(food_id: str) -> dict:
    """Delete a food."""
    client = get_client()
    await client.delete_food(food_id)
    return {"status": "deleted", "id": food_id}


@register_tool("core", "full")
async def merge_foods(from_food_id: str, to_food_id: str) -> dict:
    """Merge one food into another. All references to from_food become to_food."""
    client = get_client()
    return await client.merge_foods(from_food_id, to_food_id)


# =============================================================================
# Unit Tools
# =============================================================================

@register_tool("core", "full")
async def get_units(page: int = 1, per_page: int = 50) -> dict:
    """Get all measurement units."""
    client = get_client()
    return await client.get_units(page=page, per_page=per_page)


@register_tool("core", "full")
async def get_unit(unit_id: str) -> dict:
    """Get a specific unit by ID."""
    client = get_client()
    return await client.get_unit(unit_id)


@register_tool("core", "full")
async def create_unit(
    name: str,
    abbreviation: str = "",
    fraction: bool = True,
    plural_name: str | None = None,
    plural_abbreviation: str | None = None,
    use_abbreviation: bool | None = None,
) -> dict:
    """Create a new measurement unit."""
    client = get_client()
    return await client.create_unit(
        name,
        abbreviation=abbreviation,
        fraction=fraction,
        plural_name=plural_name,
        plural_abbreviation=plural_abbreviation,
        use_abbreviation=use_abbreviation,
    )


@register_tool("core", "full")
async def update_unit(
    unit_id: str,
    name: str | None = None,
    abbreviation: str | None = None,
    plural_name: str | None = None,
    plural_abbreviation: str | None = None,
    use_abbreviation: bool | None = None,
    description: str | None = None,
) -> dict:
    """Update a unit's display and metadata fields."""
    client = get_client()
    data = await client.get_unit(unit_id)
    if name is not None:
        data["name"] = name
    if abbreviation is not None:
        data["abbreviation"] = abbreviation
    if plural_name is not None:
        data["pluralName"] = plural_name
    if plural_abbreviation is not None:
        data["pluralAbbreviation"] = plural_abbreviation
    if use_abbreviation is not None:
        data["useAbbreviation"] = use_abbreviation
    if description is not None:
        data["description"] = description
    return await client.update_unit(unit_id, data)


@register_tool("core", "full")
async def delete_unit(unit_id: str) -> dict:
    """Delete a unit."""
    client = get_client()
    await client.delete_unit(unit_id)
    return {"status": "deleted", "id": unit_id}


@register_tool("core", "full")
async def merge_units(from_unit_id: str, to_unit_id: str) -> dict:
    """Merge one unit into another. All references to from_unit become to_unit."""
    client = get_client()
    return await client.merge_units(from_unit_id, to_unit_id)


# =============================================================================
# Label Tools
# =============================================================================

@register_tool("full")
async def get_labels(search: str | None = None, page: int = 1, per_page: int = 50) -> dict:
    """Get multi-purpose labels. Use search to filter by name."""
    client = get_client()
    return await client.get_labels(page=page, per_page=per_page, search=search)


@register_tool("full")
async def get_label(label_id: str) -> dict:
    """Get a specific label by ID."""
    client = get_client()
    return await client.get_label(label_id)


@register_tool("full")
async def create_label(name: str, color: str = "#E0E0E0") -> dict:
    """Create a new label with optional color (hex format)."""
    client = get_client()
    return await client.create_label(name, color)


@register_tool("full")
async def update_label(label_id: str, name: str | None = None, color: str | None = None) -> dict:
    """Update a label's name or color."""
    client = get_client()
    data = await client.get_label(label_id)
    if name is not None:
        data["name"] = name
    if color is not None:
        data["color"] = color
    return await client.update_label(label_id, data)


@register_tool("full")
async def delete_label(label_id: str) -> dict:
    """Delete a label."""
    client = get_client()
    await client.delete_label(label_id)
    return {"status": "deleted", "id": label_id}


# =============================================================================
# Ingredient Parser Tools
# =============================================================================

@register_tool("core", "full")
async def parse_ingredient(ingredient_text: str) -> dict:
    """
    Parse an ingredient string into structured data.
    
    Example: "2 cups all-purpose flour" -> {quantity: 2, unit: "cup", food: "flour"}
    """
    client = get_client()
    return await client.parse_ingredient(ingredient_text)


@register_tool("core", "full")
async def parse_ingredients(ingredients: list[str]) -> list[dict]:
    """Parse multiple ingredient strings in one request."""
    client = get_client()
    return await client.parse_ingredients(ingredients)


@register_tool("core", "full")
async def formalize_recipe_ingredients(
    slug: str,
    create_missing_foods: bool = True,
    create_missing_units: bool = False,
    link_ingredients_to_steps: bool = True,
) -> dict:
    """
    Parse and formalize recipe ingredients into structured fields.

    This tool safely resolves parser output to real Mealie food/unit records before writing.
    It can also link ingredient references to instruction steps.
    """
    client = get_client()
    recipe = await client.get_recipe(slug)
    ingredients = recipe.get("recipeIngredient", [])
    if not ingredients:
        return {
            "slug": slug,
            "updated_ingredients": 0,
            "created_foods": 0,
            "created_units": 0,
            "linked_steps": 0,
            "status": "no-ingredients",
        }

    ingredient_text = [
        i.get("note") or i.get("display") or i.get("originalText") or ""
        for i in ingredients
    ]
    parsed = await client.parse_ingredients(ingredient_text)

    # Cache foods by normalized name.
    food_cache: dict[str, dict] = {}
    foods_page = await client.get_foods(page=1, per_page=250)
    for f in foods_page.get("items", []):
        name = (f.get("name") or "").strip().lower()
        if name:
            food_cache[name] = f

    # Cache units by normalized name and abbreviation.
    unit_cache: dict[str, dict] = {}
    units_page = await client.get_units(page=1, per_page=250)
    for u in units_page.get("items", []):
        n = (u.get("name") or "").strip().lower()
        a = (u.get("abbreviation") or "").strip().lower()
        if n:
            unit_cache[n] = u
        if a:
            unit_cache[a] = u

    created_foods = 0
    created_units = 0
    updated = []
    ref_tokens: list[tuple[str, str]] = []

    for original, parsed_item in zip(ingredients, parsed if isinstance(parsed, list) else []):
        p_ing = parsed_item.get("ingredient", {}) if isinstance(parsed_item, dict) else {}
        ing = dict(original)

        # Quantity/note are generally safe to normalize.
        if p_ing.get("quantity") is not None:
            ing["quantity"] = p_ing["quantity"]
        if p_ing.get("note"):
            ing["note"] = p_ing["note"]

        # Resolve food by parser name -> existing DB entry (or create).
        p_food = p_ing.get("food") if isinstance(p_ing.get("food"), dict) else None
        food_name = (p_food.get("name") if p_food else "") or ""
        food_name_key = food_name.strip().lower()
        resolved_food = food_cache.get(food_name_key)
        if not resolved_food and food_name_key:
            search = await client.get_foods(page=1, per_page=25, search=food_name)
            for candidate in search.get("items", []):
                if (candidate.get("name") or "").strip().lower() == food_name_key:
                    resolved_food = candidate
                    break
        if not resolved_food and food_name_key and create_missing_foods:
            resolved_food = await client.create_food(name=food_name, description="")
            food_cache[food_name_key] = resolved_food
            created_foods += 1
        if resolved_food and resolved_food.get("id"):
            ing["foodId"] = resolved_food["id"]
            ing["food"] = {"id": resolved_food["id"], "name": resolved_food.get("name")}

        # Resolve unit by parser name/abbr -> existing DB entry (or create).
        p_unit = p_ing.get("unit") if isinstance(p_ing.get("unit"), dict) else None
        unit_name = (p_unit.get("name") if p_unit else "") or ""
        unit_abbr = (p_unit.get("abbreviation") if p_unit else "") or ""
        unit_key = (unit_name or unit_abbr).strip().lower()
        resolved_unit = unit_cache.get(unit_key) if unit_key else None
        if not resolved_unit and unit_name:
            # Fallback exact-name lookup across current page cache.
            for k, candidate in unit_cache.items():
                if k == unit_name.strip().lower() and candidate.get("id"):
                    resolved_unit = candidate
                    break
        if not resolved_unit and unit_name and create_missing_units:
            resolved_unit = await client.create_unit(
                name=unit_name,
                abbreviation=unit_abbr,
                fraction=True,
            )
            if unit_name.strip():
                unit_cache[unit_name.strip().lower()] = resolved_unit
            if unit_abbr.strip():
                unit_cache[unit_abbr.strip().lower()] = resolved_unit
            created_units += 1
        if resolved_unit and resolved_unit.get("id"):
            ing["unitId"] = resolved_unit["id"]
            ing["unit"] = {
                "id": resolved_unit["id"],
                "name": resolved_unit.get("name"),
                "abbreviation": resolved_unit.get("abbreviation"),
            }

        updated.append(ing)

        ref_id = ing.get("referenceId")
        token = (
            ((ing.get("food") or {}).get("name") if isinstance(ing.get("food"), dict) else "")
            or ing.get("note")
            or ""
        ).strip().lower()
        if ref_id and token:
            ref_tokens.append((token, ref_id))

    # Persist ingredient formalization.
    await client.patch_recipe(slug, {"recipeIngredient": updated})

    linked_steps = 0
    if link_ingredients_to_steps:
        fresh = await client.get_recipe(slug)
        steps = fresh.get("recipeInstructions", [])
        for step in steps:
            text_l = (step.get("text") or "").lower()
            refs = []
            for token, ref_id in ref_tokens:
                if len(token) < 3:
                    continue
                if token in text_l or any(w in text_l for w in re.split(r"\\s+", token) if len(w) >= 4):
                    refs.append({"referenceId": ref_id})
            seen = set()
            deduped = []
            for r in refs:
                rid = r["referenceId"]
                if rid not in seen:
                    seen.add(rid)
                    deduped.append(r)
            step["ingredientReferences"] = deduped
            if deduped:
                linked_steps += 1
        await client.patch_recipe(slug, {"recipeInstructions": steps})

    return {
        "slug": slug,
        "updated_ingredients": len(updated),
        "created_foods": created_foods,
        "created_units": created_units,
        "linked_steps": linked_steps,
        "status": "ok",
    }


@register_tool("core", "full")
async def get_recipe_cleanup_summary(slug: str) -> dict:
    """
    Summarize likely cleanup gaps after importing a recipe.

    Highlights missing organizer metadata, large/unlinked instruction blocks, and
    foods referenced by the recipe that still lack canonical metadata.
    """
    client = get_client()
    recipe = await client.get_recipe(slug)

    ingredients = recipe.get("recipeIngredient", []) or []
    instructions = recipe.get("recipeInstructions", []) or []
    categories = recipe.get("recipeCategory") or []
    tags = recipe.get("tags") or []
    tools = recipe.get("tools") or []

    ingredient_gaps = []
    food_gaps = []
    seen_food_ids: set[str] = set()

    for ingredient in ingredients:
        food = ingredient.get("food") if isinstance(ingredient.get("food"), dict) else {}
        unit = ingredient.get("unit") if isinstance(ingredient.get("unit"), dict) else {}
        display_text = (
            ingredient.get("display")
            or ingredient.get("originalText")
            or ingredient.get("note")
            or ""
        )

        missing = []
        if ingredient.get("quantity") in (None, "") and _text_mentions_quantity(display_text):
            missing.append("quantity")
        if not food and not ingredient.get("foodId"):
            missing.append("food")
        if not unit and not ingredient.get("unitId") and _text_starts_with_measured_unit(display_text):
            missing.append("unit")
        if missing:
            ingredient_gaps.append({
                "display": display_text,
                "referenceId": ingredient.get("referenceId"),
                "missing": missing,
            })

        food_id = ingredient.get("foodId") or food.get("id")
        if not food_id or food_id in seen_food_ids:
            continue
        seen_food_ids.add(food_id)
        try:
            full_food = await client.get_food(food_id)
        except Exception:
            continue

        missing_food_metadata = []
        if not full_food.get("pluralName"):
            missing_food_metadata.append("pluralName")
        if not full_food.get("description"):
            missing_food_metadata.append("description")
        if not full_food.get("labelId"):
            missing_food_metadata.append("label")
        if missing_food_metadata:
            label = full_food.get("label") if isinstance(full_food.get("label"), dict) else {}
            food_gaps.append({
                "id": food_id,
                "name": full_food.get("name"),
                "pluralName": full_food.get("pluralName"),
                "label": label.get("name"),
                "missing": missing_food_metadata,
            })

    instruction_text_lengths = [
        len((step.get("text") or "").strip())
        for step in instructions
        if isinstance(step, dict)
    ]
    unlinked_instruction_count = sum(
        1
        for step in instructions
        if isinstance(step, dict) and not step.get("ingredientReferences")
    )
    one_big_instruction = (
        len(instructions) == 1
        and bool(instruction_text_lengths)
        and instruction_text_lengths[0] >= 500
    )

    return {
        "slug": slug,
        "name": recipe.get("name"),
        "organizers": {
            "categories": [item.get("name") for item in categories],
            "tags": [item.get("name") for item in tags],
            "tools": [item.get("name") for item in tools],
            "missing": {
                "categories": not bool(categories),
                "tags": not bool(tags),
                "tools": not bool(tools),
            },
        },
        "ingredients": {
            "count": len(ingredients),
            "gaps": ingredient_gaps,
        },
        "foods": {
            "referenced_count": len(seen_food_ids),
            "metadata_gaps": food_gaps,
        },
        "instructions": {
            "count": len(instructions),
            "unlinked_count": unlinked_instruction_count,
            "one_big_instruction": one_big_instruction,
            "text_lengths": instruction_text_lengths,
        },
    }




# =============================================================================
# Entry Point
# =============================================================================

if __name__ == "__main__":
    mcp.run()
