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
async def get_categories(page: int = 1, per_page: int = 50) -> dict:
    """Get all recipe categories."""
    client = get_client()
    return await client.get_categories(page=page, per_page=per_page)


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
async def get_tags(page: int = 1, per_page: int = 50) -> dict:
    """Get all recipe tags."""
    client = get_client()
    return await client.get_tags(page=page, per_page=per_page)


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
async def get_tools(page: int = 1, per_page: int = 50) -> dict:
    """Get all kitchen tools/equipment."""
    client = get_client()
    return await client.get_tools(page=page, per_page=per_page)


@register_tool("core", "full")
async def get_tool(tool_id: str) -> dict:
    """Get a specific tool by ID."""
    client = get_client()
    return await client.get_tool(tool_id)


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
async def create_food(name: str, description: str = "") -> dict:
    """Create a new food/ingredient."""
    client = get_client()
    return await client.create_food(name, description)


@register_tool("core", "full")
async def update_food(food_id: str, name: str | None = None, description: str | None = None) -> dict:
    """Update a food's name or description."""
    client = get_client()
    data = await client.get_food(food_id)
    if name is not None:
        data["name"] = name
    if description is not None:
        data["description"] = description
    return await client.update_food(food_id, data)


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
async def create_unit(name: str, abbreviation: str = "", fraction: bool = True) -> dict:
    """Create a new measurement unit."""
    client = get_client()
    return await client.create_unit(name, abbreviation=abbreviation, fraction=fraction)


@register_tool("core", "full")
async def update_unit(unit_id: str, name: str | None = None, abbreviation: str | None = None) -> dict:
    """Update a unit's name or abbreviation."""
    client = get_client()
    data = await client.get_unit(unit_id)
    if name is not None:
        data["name"] = name
    if abbreviation is not None:
        data["abbreviation"] = abbreviation
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
async def get_labels(page: int = 1, per_page: int = 50) -> dict:
    """Get all multi-purpose labels."""
    client = get_client()
    return await client.get_labels(page=page, per_page=per_page)


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




# =============================================================================
# Entry Point
# =============================================================================

if __name__ == "__main__":
    mcp.run()
