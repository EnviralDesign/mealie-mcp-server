#!/usr/bin/env python3
"""
CLI test harness for Mealie MCP Server.

This allows direct testing of MCP tools from the command line without
needing the MCP Inspector GUI.

Usage:
    uv run python test_cli.py                     # Run all tests
    uv run python test_cli.py get_recipes         # Run specific tool
    uv run python test_cli.py parse_ingredient "2 cups flour"
"""

import asyncio
import json
import sys
from typing import Any

# Import the server and tools directly
from mealie_mcp.server import mcp
from mealie_mcp.client import get_client


async def call_tool(tool_name: str, **kwargs) -> Any:
    """Call an MCP tool directly and return the result."""
    # Get the tool function from the server
    tool = None
    for t in mcp._tool_manager._tools.values():
        if t.name == tool_name:
            tool = t
            break
    
    if tool is None:
        raise ValueError(f"Tool '{tool_name}' not found. Available: {list_tools()}")
    
    # Call the tool function directly
    result = await tool.fn(**kwargs)
    return result


def list_tools() -> list[str]:
    """List all available tool names."""
    return [t.name for t in mcp._tool_manager._tools.values()]


async def test_get_recipes():
    """Test: Get recipes list."""
    print("\n📋 Testing get_recipes...")
    result = await call_tool("get_recipes", per_page=5)
    print(f"   Found {len(result.get('items', []))} recipes (showing up to 5)")
    for recipe in result.get("items", [])[:5]:
        print(f"   - {recipe.get('name')} ({recipe.get('slug')})")
    return result


async def test_get_recipe(slug: str):
    """Test: Get a single recipe."""
    print(f"\n🍳 Testing get_recipe('{slug}')...")
    result = await call_tool("get_recipe", slug=slug)
    print(f"   Name: {result.get('name')}")
    print(f"   Description: {result.get('description', 'N/A')[:100]}...")
    ingredients = result.get("recipeIngredient", [])
    print(f"   Ingredients: {len(ingredients)} items")
    return result


async def test_get_categories():
    """Test: Get categories."""
    print("\n📁 Testing get_categories...")
    result = await call_tool("get_categories", per_page=10)
    print(f"   Found {len(result.get('items', []))} categories")
    for cat in result.get("items", [])[:10]:
        print(f"   - {cat.get('name')} ({cat.get('slug')})")
    return result


async def test_get_tags():
    """Test: Get tags."""
    print("\n🏷️  Testing get_tags...")
    result = await call_tool("get_tags", per_page=10)
    print(f"   Found {len(result.get('items', []))} tags")
    for tag in result.get("items", [])[:10]:
        print(f"   - {tag.get('name')} ({tag.get('slug')})")
    return result


async def test_get_shopping_lists():
    """Test: Get shopping lists."""
    print("\n🛒 Testing get_shopping_lists...")
    result = await call_tool("get_shopping_lists")
    print(f"   Found {len(result.get('items', []))} shopping lists")
    for lst in result.get("items", []):
        print(f"   - {lst.get('name')} (ID: {lst.get('id')})")
    return result


async def test_parse_ingredient(text: str):
    """Test: Parse an ingredient string."""
    print(f"\n🥄 Testing parse_ingredient('{text}')...")
    result = await call_tool("parse_ingredient", ingredient_text=text)
    print(f"   Parsed result:")
    print(f"   - Quantity: {result.get('ingredient', {}).get('quantity')}")
    print(f"   - Unit: {result.get('ingredient', {}).get('unit', {}).get('name') if result.get('ingredient', {}).get('unit') else 'N/A'}")
    print(f"   - Food: {result.get('ingredient', {}).get('food', {}).get('name') if result.get('ingredient', {}).get('food') else 'N/A'}")
    print(f"   - Note: {result.get('ingredient', {}).get('note', 'N/A')}")
    return result


async def test_get_foods():
    """Test: Get foods database."""
    print("\n🥕 Testing get_foods...")
    result = await call_tool("get_foods", per_page=10)
    print(f"   Found {result.get('total', 0)} total foods (showing 10)")
    for food in result.get("items", [])[:10]:
        print(f"   - {food.get('name')}")
    return result


async def test_get_units():
    """Test: Get measurement units."""
    print("\n📏 Testing get_units...")
    result = await call_tool("get_units", per_page=10)
    print(f"   Found {result.get('total', 0)} total units (showing 10)")
    for unit in result.get("items", [])[:10]:
        print(f"   - {unit.get('name')} ({unit.get('abbreviation', 'N/A')})")
    return result


async def run_all_tests():
    """Run all basic tests."""
    print("=" * 60)
    print("🧪 MEALIE MCP SERVER - CLI TEST HARNESS")
    print("=" * 60)
    
    print(f"\n📦 Available tools: {', '.join(list_tools())}")
    
    errors = []
    
    # Test each tool
    try:
        recipes = await test_get_recipes()
        
        # If we have recipes, test getting one
        if recipes.get("items"):
            first_slug = recipes["items"][0]["slug"]
            await test_get_recipe(first_slug)
    except Exception as e:
        errors.append(f"Recipes: {e}")
        print(f"   ❌ Error: {e}")
    
    try:
        await test_get_categories()
    except Exception as e:
        errors.append(f"Categories: {e}")
        print(f"   ❌ Error: {e}")
    
    try:
        await test_get_tags()
    except Exception as e:
        errors.append(f"Tags: {e}")
        print(f"   ❌ Error: {e}")
    
    try:
        await test_get_shopping_lists()
    except Exception as e:
        errors.append(f"Shopping Lists: {e}")
        print(f"   ❌ Error: {e}")
    
    try:
        await test_get_foods()
    except Exception as e:
        errors.append(f"Foods: {e}")
        print(f"   ❌ Error: {e}")
    
    try:
        await test_get_units()
    except Exception as e:
        errors.append(f"Units: {e}")
        print(f"   ❌ Error: {e}")
    
    try:
        await test_parse_ingredient("2 cups all-purpose flour")
    except Exception as e:
        errors.append(f"Parse Ingredient: {e}")
        print(f"   ❌ Error: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    if errors:
        print(f"❌ COMPLETED WITH {len(errors)} ERRORS:")
        for err in errors:
            print(f"   - {err}")
    else:
        print("✅ ALL TESTS PASSED!")
    print("=" * 60)


async def main():
    """Main entry point."""
    args = sys.argv[1:]
    
    if not args:
        # Run all tests
        await run_all_tests()
    elif args[0] == "--list":
        print("Available tools:")
        for name in list_tools():
            print(f"  - {name}")
    elif args[0] == "parse_ingredient" and len(args) > 1:
        await test_parse_ingredient(" ".join(args[1:]))
    elif args[0] == "get_recipe" and len(args) > 1:
        await test_get_recipe(args[1])
    elif args[0] in list_tools():
        # Generic tool call
        tool_name = args[0]
        print(f"Calling {tool_name}...")
        result = await call_tool(tool_name)
        print(json.dumps(result, indent=2, default=str))
    else:
        print(f"Unknown command: {args[0]}")
        print("Usage:")
        print("  uv run python test_cli.py                     # Run all tests")
        print("  uv run python test_cli.py --list              # List tools")
        print("  uv run python test_cli.py get_recipes         # Call specific tool")
        print("  uv run python test_cli.py parse_ingredient \"2 cups flour\"")


if __name__ == "__main__":
    asyncio.run(main())
