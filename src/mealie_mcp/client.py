"""Mealie API Client - Handles authentication and HTTP requests to Mealie."""

import os
from typing import Any

import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class MealieClient:
    """HTTP client for interacting with the Mealie API."""
    
    def __init__(
        self,
        base_url: str | None = None,
        api_token: str | None = None,
    ):
        """
        Initialize the Mealie client.
        
        Args:
            base_url: Mealie instance URL (defaults to MEALIE_URL env var)
            api_token: API token for authentication (defaults to MEALIE_API_TOKEN env var)
        """
        self.base_url = (base_url or os.getenv("MEALIE_URL", "http://localhost:9000")).rstrip("/")
        self.api_token = api_token or os.getenv("MEALIE_API_TOKEN", "")
        
        if not self.api_token:
            raise ValueError(
                "MEALIE_API_TOKEN is required. "
                "Generate one in Mealie: User Settings > API Tokens"
            )
        
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=30.0,
        )

    @staticmethod
    def _raise_for_status_with_body(response: httpx.Response) -> None:
        """Raise HTTPStatusError with response body context when available."""
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            body_snippet = ""
            try:
                body = response.text.strip()
                if body:
                    body_snippet = body[:1000]
            except Exception:
                body_snippet = ""

            detail = (
                f"{response.request.method} {response.request.url} -> {response.status_code}"
            )
            if body_snippet:
                detail += f" | body: {body_snippet}"
            raise httpx.HTTPStatusError(detail, request=exc.request, response=exc.response) from exc
    
    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, *args):
        await self.close()
    
    # =========================================================================
    # Generic HTTP Methods
    # =========================================================================
    
    async def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Send a GET request."""
        response = await self._client.get(path, params=params)
        self._raise_for_status_with_body(response)
        return response.json()
    
    async def post(self, path: str, data: dict[str, Any] | None = None) -> Any:
        """Send a POST request."""
        response = await self._client.post(path, json=data)
        self._raise_for_status_with_body(response)
        # Some endpoints return empty responses
        if response.content:
            return response.json()
        return None
    
    async def put(self, path: str, data: dict[str, Any] | None = None) -> Any:
        """Send a PUT request."""
        response = await self._client.put(path, json=data)
        self._raise_for_status_with_body(response)
        if response.content:
            return response.json()
        return None
    
    async def patch(self, path: str, data: dict[str, Any] | None = None) -> Any:
        """Send a PATCH request."""
        response = await self._client.patch(path, json=data)
        self._raise_for_status_with_body(response)
        if response.content:
            return response.json()
        return None
    
    async def delete(self, path: str) -> Any:
        """Send a DELETE request."""
        response = await self._client.delete(path)
        self._raise_for_status_with_body(response)
        if response.content:
            return response.json()
        return None
    
    # =========================================================================
    # Recipe Methods
    # =========================================================================
    
    async def get_recipes(
        self,
        page: int = 1,
        per_page: int = 50,
        search: str | None = None,
        categories: list[str] | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Get a paginated list of recipes.
        
        Args:
            page: Page number (1-indexed)
            per_page: Number of items per page
            search: Search query
            categories: Filter by category slugs/IDs
            tags: Filter by tag slugs/IDs
        """
        params: dict[str, Any] = {
            "page": page,
            "perPage": per_page,
        }
        if search:
            params["search"] = search
        if categories:
            params["categories"] = categories
        if tags:
            params["tags"] = tags
        
        return await self.get("/api/recipes", params=params)
    
    async def get_recipe(self, slug: str) -> dict[str, Any]:
        """Get a single recipe by slug or ID."""
        return await self.get(f"/api/recipes/{slug}")
    
    async def create_recipe(self, data: dict[str, Any]) -> str:
        """
        Create a new recipe.
        
        Args:
            data: Recipe data (name is required)
            
        Returns:
            The slug of the created recipe
        """
        return await self.post("/api/recipes", data=data)
    
    async def update_recipe(self, slug: str, data: dict[str, Any]) -> dict[str, Any]:
        """Update an existing recipe."""
        return await self.put(f"/api/recipes/{slug}", data=data)
    
    async def patch_recipe(self, slug: str, data: dict[str, Any]) -> dict[str, Any]:
        """Partially update a recipe."""
        return await self.patch(f"/api/recipes/{slug}", data=data)
    
    async def delete_recipe(self, slug: str) -> None:
        """Delete a recipe."""
        await self.delete(f"/api/recipes/{slug}")
    
    async def import_recipe_from_url(self, url: str, include_tags: bool = False) -> str:
        """Import a recipe from a URL."""
        return await self.post("/api/recipes/create/url", data={
            "url": url,
            "includeTags": include_tags,
        })
    
    async def duplicate_recipe(self, slug: str) -> str:
        """Duplicate a recipe. Returns the new recipe's slug."""
        # Some Mealie builds require a JSON body (even if empty) for this endpoint.
        result = await self.post(f"/api/recipes/{slug}/duplicate", data={})
        if isinstance(result, str):
            return result
        if isinstance(result, dict):
            duplicated_slug = result.get("slug")
            if isinstance(duplicated_slug, str):
                return duplicated_slug
        raise ValueError("Unexpected response shape from duplicate recipe endpoint")
    
    async def test_scrape_url(self, url: str) -> dict[str, Any]:
        """Test scraping a URL without saving the recipe."""
        return await self.post("/api/recipes/test-scrape-url", data={"url": url})
    
    async def set_recipe_last_made(self, slug: str, date: str) -> dict[str, Any]:
        """Set when a recipe was last made. Date format: YYYY-MM-DD"""
        return await self.patch(f"/api/recipes/{slug}/last-made", data={"timestamp": date})
    
    async def get_recipe_suggestions(self) -> dict[str, Any]:
        """Get recipe suggestions based on mealplan rules."""
        return await self.get("/api/recipes/suggestions")
    
    # =========================================================================
    # Recipe Bulk Actions
    # =========================================================================
    
    async def bulk_tag_recipes(self, recipe_ids: list[str], tags: list[dict]) -> dict[str, Any]:
        """Add tags to multiple recipes."""
        return await self.post("/api/recipes/bulk-actions/tag", data={
            "recipes": recipe_ids,
            "tags": tags,
        })
    
    async def bulk_categorize_recipes(self, recipe_ids: list[str], categories: list[dict]) -> dict[str, Any]:
        """Add categories to multiple recipes."""
        return await self.post("/api/recipes/bulk-actions/categorize", data={
            "recipes": recipe_ids,
            "categories": categories,
        })
    
    async def bulk_delete_recipes(self, recipe_ids: list[str]) -> dict[str, Any]:
        """Delete multiple recipes."""
        return await self.post("/api/recipes/bulk-actions/delete", data={
            "recipes": recipe_ids,
        })
    
    async def bulk_export_recipes(self, recipe_ids: list[str]) -> dict[str, Any]:
        """Export multiple recipes."""
        return await self.post("/api/recipes/bulk-actions/export", data={
            "recipeIds": recipe_ids,
        })
    
    async def bulk_update_recipe_settings(self, recipe_ids: list[str], settings: dict) -> dict[str, Any]:
        """Update settings for multiple recipes."""
        return await self.post("/api/recipes/bulk-actions/settings", data={
            "recipeIds": recipe_ids,
            "settings": settings,
        })
    
    # =========================================================================
    # Shopping List Methods
    # =========================================================================
    
    async def get_shopping_lists(self, page: int = 1, per_page: int = 50) -> dict[str, Any]:
        """Get all shopping lists."""
        return await self.get("/api/households/shopping/lists", params={
            "page": page,
            "perPage": per_page,
        })
    
    async def get_shopping_list(self, list_id: str) -> dict[str, Any]:
        """Get a shopping list by ID."""
        return await self.get(f"/api/households/shopping/lists/{list_id}")
    
    async def create_shopping_list(self, name: str) -> dict[str, Any]:
        """Create a new shopping list."""
        return await self.post("/api/households/shopping/lists", data={"name": name})
    
    async def update_shopping_list(self, list_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Update a shopping list."""
        return await self.put(f"/api/households/shopping/lists/{list_id}", data=data)
    
    async def delete_shopping_list(self, list_id: str) -> None:
        """Delete a shopping list."""
        await self.delete(f"/api/households/shopping/lists/{list_id}")
    
    async def add_recipe_to_shopping_list(
        self,
        list_id: str,
        recipe_id: str,
        scale: float = 1.0,
    ) -> dict[str, Any]:
        """Add all ingredients from a recipe to a shopping list."""
        return await self.post(
            f"/api/households/shopping/lists/{list_id}/recipe",
            data=[{"recipeId": recipe_id, "scale": scale}],
        )
    
    async def remove_recipe_from_shopping_list(self, list_id: str, recipe_id: str) -> dict[str, Any]:
        """Remove recipe ingredients from a shopping list."""
        return await self.post(f"/api/households/shopping/lists/{list_id}/recipe/{recipe_id}/delete")
    
    # =========================================================================
    # Shopping List Items
    # =========================================================================
    
    async def get_shopping_items(self, page: int = 1, per_page: int = 50) -> dict[str, Any]:
        """Get all shopping items."""
        return await self.get("/api/households/shopping/items", params={
            "page": page,
            "perPage": per_page,
        })
    
    async def get_shopping_item(self, item_id: str) -> dict[str, Any]:
        """Get a shopping item by ID."""
        return await self.get(f"/api/households/shopping/items/{item_id}")
    
    async def add_shopping_item(
        self,
        shopping_list_id: str,
        note: str,
        quantity: float = 1,
        unit: str | None = None,
        food: str | None = None,
        checked: bool = False,
    ) -> dict[str, Any]:
        """Add an item to a shopping list."""
        data: dict[str, Any] = {
            "shoppingListId": shopping_list_id,
            "note": note,
            "quantity": quantity,
            "checked": checked,
        }
        if unit:
            data["unit"] = {"name": unit}
        if food:
            data["food"] = {"name": food}
        return await self.post("/api/households/shopping/items", data=data)
    
    async def add_shopping_items_bulk(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Add multiple items to a shopping list."""
        return await self.post("/api/households/shopping/items/create-bulk", data=items)
    
    async def update_shopping_item(self, item_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Update a shopping item."""
        return await self.put(f"/api/households/shopping/items/{item_id}", data=data)
    
    async def delete_shopping_item(self, item_id: str) -> None:
        """Delete a shopping item."""
        await self.delete(f"/api/households/shopping/items/{item_id}")
    
    async def delete_shopping_items_bulk(self, item_ids: list[str]) -> None:
        """Delete multiple shopping items."""
        await self.delete("/api/households/shopping/items")
    
    # =========================================================================
    # Categories
    # =========================================================================
    
    async def get_categories(self, page: int = 1, per_page: int = 50) -> dict[str, Any]:
        """Get all recipe categories."""
        return await self.get("/api/organizers/categories", params={
            "page": page,
            "perPage": per_page,
        })
    
    async def get_category(self, category_id: str) -> dict[str, Any]:
        """Get a category by ID."""
        return await self.get(f"/api/organizers/categories/{category_id}")
    
    async def get_category_by_slug(self, slug: str) -> dict[str, Any]:
        """Get a category by slug."""
        return await self.get(f"/api/organizers/categories/slug/{slug}")
    
    async def get_empty_categories(self) -> dict[str, Any]:
        """Get categories with no recipes."""
        return await self.get("/api/organizers/categories/empty")
    
    async def create_category(self, name: str) -> dict[str, Any]:
        """Create a new category."""
        return await self.post("/api/organizers/categories", data={"name": name})
    
    async def update_category(self, category_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Update a category."""
        return await self.put(f"/api/organizers/categories/{category_id}", data=data)
    
    async def delete_category(self, category_id: str) -> None:
        """Delete a category."""
        await self.delete(f"/api/organizers/categories/{category_id}")
    
    # =========================================================================
    # Tags
    # =========================================================================
    
    async def get_tags(self, page: int = 1, per_page: int = 50) -> dict[str, Any]:
        """Get all recipe tags."""
        return await self.get("/api/organizers/tags", params={
            "page": page,
            "perPage": per_page,
        })
    
    async def get_tag(self, tag_id: str) -> dict[str, Any]:
        """Get a tag by ID."""
        return await self.get(f"/api/organizers/tags/{tag_id}")
    
    async def get_tag_by_slug(self, slug: str) -> dict[str, Any]:
        """Get a tag by slug."""
        return await self.get(f"/api/organizers/tags/slug/{slug}")
    
    async def get_empty_tags(self) -> dict[str, Any]:
        """Get tags with no recipes."""
        return await self.get("/api/organizers/tags/empty")
    
    async def create_tag(self, name: str) -> dict[str, Any]:
        """Create a new tag."""
        return await self.post("/api/organizers/tags", data={"name": name})
    
    async def update_tag(self, tag_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Update a tag."""
        return await self.put(f"/api/organizers/tags/{tag_id}", data=data)
    
    async def delete_tag(self, tag_id: str) -> None:
        """Delete a tag."""
        await self.delete(f"/api/organizers/tags/{tag_id}")
    
    # =========================================================================
    # Tools (Kitchen Equipment)
    # =========================================================================
    
    async def get_tools(self, page: int = 1, per_page: int = 50) -> dict[str, Any]:
        """Get all kitchen tools."""
        return await self.get("/api/organizers/tools", params={
            "page": page,
            "perPage": per_page,
        })
    
    async def get_tool(self, tool_id: str) -> dict[str, Any]:
        """Get a tool by ID."""
        return await self.get(f"/api/organizers/tools/{tool_id}")
    
    async def get_tool_by_slug(self, slug: str) -> dict[str, Any]:
        """Get a tool by slug."""
        return await self.get(f"/api/organizers/tools/slug/{slug}")
    
    async def create_tool(self, name: str) -> dict[str, Any]:
        """Create a new tool."""
        return await self.post("/api/organizers/tools", data={"name": name})
    
    async def update_tool(self, tool_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Update a tool."""
        return await self.put(f"/api/organizers/tools/{tool_id}", data=data)
    
    async def delete_tool(self, tool_id: str) -> None:
        """Delete a tool."""
        await self.delete(f"/api/organizers/tools/{tool_id}")
    
    # =========================================================================
    # Foods
    # =========================================================================
    
    async def get_foods(self, page: int = 1, per_page: int = 50, search: str | None = None) -> dict[str, Any]:
        """Get all foods/ingredients."""
        params = {"page": page, "perPage": per_page}
        if search:
            params["search"] = search
        return await self.get("/api/foods", params=params)
    
    async def get_food(self, food_id: str) -> dict[str, Any]:
        """Get a food by ID."""
        return await self.get(f"/api/foods/{food_id}")
    
    async def create_food(self, name: str, description: str = "", label_id: str | None = None) -> dict[str, Any]:
        """Create a new food."""
        data: dict[str, Any] = {"name": name, "description": description}
        if label_id:
            data["labelId"] = label_id
        return await self.post("/api/foods", data=data)
    
    async def update_food(self, food_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Update a food."""
        return await self.put(f"/api/foods/{food_id}", data=data)
    
    async def delete_food(self, food_id: str) -> None:
        """Delete a food."""
        await self.delete(f"/api/foods/{food_id}")
    
    async def merge_foods(self, from_food_id: str, to_food_id: str) -> dict[str, Any]:
        """Merge one food into another."""
        return await self.put("/api/foods/merge", data={
            "fromFood": from_food_id,
            "toFood": to_food_id,
        })
    
    # =========================================================================
    # Units
    # =========================================================================
    
    async def get_units(self, page: int = 1, per_page: int = 50) -> dict[str, Any]:
        """Get all measurement units."""
        return await self.get("/api/units", params={
            "page": page,
            "perPage": per_page,
        })
    
    async def get_unit(self, unit_id: str) -> dict[str, Any]:
        """Get a unit by ID."""
        return await self.get(f"/api/units/{unit_id}")
    
    async def create_unit(
        self,
        name: str,
        abbreviation: str = "",
        description: str = "",
        fraction: bool = True,
    ) -> dict[str, Any]:
        """Create a new unit."""
        return await self.post("/api/units", data={
            "name": name,
            "abbreviation": abbreviation,
            "description": description,
            "fraction": fraction,
        })
    
    async def update_unit(self, unit_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Update a unit."""
        return await self.put(f"/api/units/{unit_id}", data=data)
    
    async def delete_unit(self, unit_id: str) -> None:
        """Delete a unit."""
        await self.delete(f"/api/units/{unit_id}")
    
    async def merge_units(self, from_unit_id: str, to_unit_id: str) -> dict[str, Any]:
        """Merge one unit into another."""
        return await self.put("/api/units/merge", data={
            "fromUnit": from_unit_id,
            "toUnit": to_unit_id,
        })
    
    # =========================================================================
    # Labels
    # =========================================================================
    
    async def get_labels(self, page: int = 1, per_page: int = 50) -> dict[str, Any]:
        """Get all multi-purpose labels."""
        return await self.get("/api/groups/labels", params={
            "page": page,
            "perPage": per_page,
        })
    
    async def get_label(self, label_id: str) -> dict[str, Any]:
        """Get a label by ID."""
        return await self.get(f"/api/groups/labels/{label_id}")
    
    async def create_label(self, name: str, color: str = "#E0E0E0") -> dict[str, Any]:
        """Create a new label."""
        return await self.post("/api/groups/labels", data={
            "name": name,
            "color": color,
        })
    
    async def update_label(self, label_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Update a label."""
        return await self.put(f"/api/groups/labels/{label_id}", data=data)
    
    async def delete_label(self, label_id: str) -> None:
        """Delete a label."""
        await self.delete(f"/api/groups/labels/{label_id}")
    
    # =========================================================================
    # Ingredient Parser
    # =========================================================================
    
    async def parse_ingredient(self, ingredient_text: str) -> dict[str, Any]:
        """Parse an ingredient string into structured data."""
        return await self.post("/api/parser/ingredient", data={
            "ingredient": ingredient_text,
        })
    
    async def parse_ingredients(self, ingredients: list[str]) -> list[dict[str, Any]]:
        """Parse multiple ingredient strings."""
        return await self.post("/api/parser/ingredients", data={
            "ingredients": ingredients,
        })


# Global client instance (initialized lazily)
_client: MealieClient | None = None


def get_client() -> MealieClient:
    """Get the global Mealie client instance."""
    global _client
    if _client is None:
        _client = MealieClient()
    return _client
