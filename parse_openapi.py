#!/usr/bin/env python3
"""
Parse Mealie OpenAPI spec and generate a categorized API endpoint document.
"""

import json
from collections import defaultdict
from pathlib import Path


def load_openapi_spec(path: str) -> dict:
    """Load the OpenAPI spec from a JSON file."""
    with open(path, "r") as f:
        return json.load(f)


def extract_endpoints(spec: dict) -> list[dict]:
    """Extract all endpoints from the OpenAPI spec."""
    endpoints = []
    
    for path, methods in spec.get("paths", {}).items():
        for method, details in methods.items():
            if method in ("get", "post", "put", "patch", "delete"):
                endpoint = {
                    "path": path,
                    "method": method.upper(),
                    "operation_id": details.get("operationId", ""),
                    "summary": details.get("summary", ""),
                    "description": details.get("description", ""),
                    "tags": details.get("tags", []),
                    "deprecated": details.get("deprecated", False),
                    "requires_auth": bool(details.get("security")),
                    "parameters": [],
                    "request_body": None,
                }
                
                # Extract parameters
                for param in details.get("parameters", []):
                    endpoint["parameters"].append({
                        "name": param.get("name"),
                        "in": param.get("in"),
                        "required": param.get("required", False),
                        "type": param.get("schema", {}).get("type", "unknown"),
                    })
                
                # Check for request body
                if "requestBody" in details:
                    endpoint["request_body"] = True
                
                endpoints.append(endpoint)
    
    return endpoints


def categorize_endpoints(endpoints: list[dict]) -> dict[str, list[dict]]:
    """Group endpoints by their primary tag."""
    categories = defaultdict(list)
    
    for endpoint in endpoints:
        if endpoint["tags"]:
            primary_tag = endpoint["tags"][0]
        else:
            primary_tag = "Uncategorized"
        categories[primary_tag].append(endpoint)
    
    return dict(sorted(categories.items()))


def assign_priority(tag: str, endpoint: dict) -> tuple[int, str]:
    """
    Assign a priority score to an endpoint.
    Lower score = higher priority.
    
    Priority factors:
    - Core recipe operations (highest priority)
    - Shopping lists and meal planning
    - User management and authentication
    - Foods, units, categories, tags (recipe organization)
    - Administrative functions (lower priority)
    """
    priority_map = {
        # Tier 1: Core Recipe Operations (1-10)
        "Recipe: CRUD": 1,
        "Recipe: Comments": 5,
        "Recipe: Timeline": 6,
        "Recipe: Bulk Actions": 7,
        "Recipe: Exports": 8,
        "Recipe: Shared": 9,
        "Recipe: Images and Assets": 10,
        
        # Tier 2: Shopping & Meal Planning (11-20)
        "Households: Shopping Lists": 11,
        "Households: Shopping List Items": 12,
        "Households: Mealplans": 13,
        "Households: Mealplan Rules": 14,
        
        # Tier 3: Recipe Organization (21-30)
        "Organizer: Categories": 21,
        "Organizers: Categories": 21,
        "Organizer: Tags": 22,
        "Organizers: Tags": 22,
        "Organizer: Tools": 23,
        "Organizers: Tools": 23,
        "Recipes: Foods": 24,
        "Foods": 24,
        "Recipe: Ingredient Parser": 25,
        "Recipes: Units": 26,
        "Units": 26,
        "Groups: Multi Purpose Labels": 27,
        "Households: Cookbooks": 28,
        
        # Tier 4: User & Auth (31-40)
        "Users: Authentication": 31,
        "Users: CRUD": 32,
        "Users: Tokens": 33,
        "Users: Registration": 34,
        "Users: Passwords": 35,
        "Users: Images": 36,
        "Users: Ratings": 37,
        
        # Tier 5: Groups & Households (41-50)
        "Households: Self Service": 41,
        "Households: Invitations": 42,
        "Groups: Self Service": 43,
        "Groups: Households": 44,
        "Groups: Reports": 45,
        "Groups: Migrations": 46,
        "Groups: Seeders": 47,
        
        # Tier 6: Webhooks & Automation (51-60)
        "Households: Webhooks": 51,
        "Households: Event Notifications": 52,
        "Households: Recipe Actions": 53,
        
        # Tier 7: Admin (61-70)
        "Admin: About": 61,
        "Admin: Manage Users": 62,
        "Admin: Manage Groups": 63,
        "Admin: Manage Households": 64,
        "Admin: Backups": 65,
        "Admin: Maintenance": 66,
        "Admin: Debug": 67,
        "Admin: Email": 69,
        
        # Tier 8: Explore/Public & Misc (71-80)
        "App: About": 71,
        "Shared: Recipes": 72,
        "Explore: Recipes": 73,
        "Explore: Foods": 74,
        "Explore: Categories": 75,
        "Explore: Tags": 75,
        "Explore: Tools": 75,
        "Explore: Cookbooks": 76,
        "Explore: Households": 77,
        "Utils": 78,
    }
    
    base_priority = priority_map.get(tag, 99)
    
    # Boost priority for common operations
    method_boost = {
        "GET": 0,
        "POST": 0.1,
        "PUT": 0.2,
        "PATCH": 0.3,
        "DELETE": 0.4,
    }
    
    return (base_priority + method_boost.get(endpoint["method"], 0), endpoint["path"])


def generate_markdown(spec: dict, endpoints: list[dict], categories: dict) -> str:
    """Generate a markdown document with all endpoints."""
    
    lines = [
        "# Mealie API Endpoints Reference",
        "",
        f"**API Version:** {spec.get('info', {}).get('version', 'Unknown')}",
        f"**Total Endpoints:** {len(endpoints)}",
        f"**Categories:** {len(categories)}",
        "",
        "---",
        "",
        "## Summary by Category",
        "",
        "| Category | Endpoint Count | Priority Tier |",
        "|----------|----------------|---------------|",
    ]
    
    # Sort categories by priority
    sorted_categories = sorted(
        categories.items(),
        key=lambda x: assign_priority(x[0], x[1][0])[0] if x[1] else 99
    )
    
    tier_names = {
        1: "🔴 Tier 1 (Core)",
        2: "🟠 Tier 2 (Shopping/Meals)",
        3: "🟡 Tier 3 (Organization)",
        4: "🟢 Tier 4 (Users/Auth)",
        5: "🔵 Tier 5 (Groups)",
        6: "🟣 Tier 6 (Automation)",
        7: "⚪ Tier 7 (Admin)",
        8: "⚫ Tier 8 (Misc)",
        9: "❓ Uncategorized",
    }
    
    for tag, eps in sorted_categories:
        priority = assign_priority(tag, eps[0])[0] if eps else 99
        tier = min(9, (int(priority) // 10) + 1)
        tier_name = tier_names.get(tier, "❓ Unknown")
        lines.append(f"| {tag} | {len(eps)} | {tier_name} |")
    
    lines.extend([
        "",
        "---",
        "",
        "## Detailed Endpoint List",
        "",
        "### Priority Legend",
        "- 🔴 **Tier 1**: Core recipe operations - highest priority",
        "- 🟠 **Tier 2**: Shopping lists & meal planning",
        "- 🟡 **Tier 3**: Recipe organization (categories, tags, foods)",
        "- 🟢 **Tier 4**: User management & authentication",
        "- 🔵 **Tier 5**: Groups & households management",
        "- 🟣 **Tier 6**: Webhooks & automation",
        "- ⚪ **Tier 7**: Administrative functions",
        "- ⚫ **Tier 8**: App info & miscellaneous",
        "",
        "---",
        "",
    ])
    
    # Detail each category
    for tag, eps in sorted_categories:
        priority = assign_priority(tag, eps[0])[0] if eps else 99
        tier = min(9, (int(priority) // 10) + 1)
        tier_emoji = ["", "🔴", "🟠", "🟡", "🟢", "🔵", "🟣", "⚪", "⚫", "❓"][tier]
        
        lines.append(f"## {tier_emoji} {tag}")
        lines.append("")
        lines.append(f"*{len(eps)} endpoints*")
        lines.append("")
        lines.append("| Method | Path | Summary | Auth | Status |")
        lines.append("|--------|------|---------|------|--------|")
        
        # Sort endpoints within category
        sorted_eps = sorted(eps, key=lambda x: (x["method"], x["path"]))
        
        for ep in sorted_eps:
            method_badge = {
                "GET": "🟢 GET",
                "POST": "🟡 POST",
                "PUT": "🔵 PUT",
                "PATCH": "🟣 PATCH",
                "DELETE": "🔴 DELETE",
            }.get(ep["method"], ep["method"])
            
            auth = "🔒" if ep["requires_auth"] else "🌐"
            status = "⚠️ Deprecated" if ep["deprecated"] else "✅"
            summary = ep["summary"] or ep["operation_id"] or "No summary"
            
            # Escape pipe characters in summary
            summary = summary.replace("|", "\\|")
            
            lines.append(f"| {method_badge} | `{ep['path']}` | {summary} | {auth} | {status} |")
        
        lines.append("")
    
    # Add implementation tracking section
    lines.extend([
        "---",
        "",
        "## Implementation Tracking",
        "",
        "Use this section to track which endpoints have been implemented as MCP tools.",
        "",
        "### Status Legend",
        "- ⬜ Not Started",
        "- 🟨 In Progress", 
        "- ✅ Implemented",
        "- ❌ Will Not Implement",
        "- 🔄 Needs Review",
        "",
        "### Tier 1: Core Recipe Operations",
        "",
        "| Endpoint | MCP Tool Name | Status | Notes |",
        "|----------|---------------|--------|-------|",
    ])
    
    # Add Tier 1 endpoints for tracking
    for tag, eps in sorted_categories:
        if "Recipe: CRUD" in tag or "Recipe: Comments" in tag:
            for ep in sorted(eps, key=lambda x: (x["method"], x["path"])):
                lines.append(f"| `{ep['method']} {ep['path']}` | | ⬜ | |")
    
    lines.extend([
        "",
        "### Tier 2: Shopping & Meal Planning",
        "",
        "| Endpoint | MCP Tool Name | Status | Notes |",
        "|----------|---------------|--------|-------|",
    ])
    
    for tag, eps in sorted_categories:
        if "Shopping" in tag or "Mealplan" in tag:
            for ep in sorted(eps, key=lambda x: (x["method"], x["path"])):
                lines.append(f"| `{ep['method']} {ep['path']}` | | ⬜ | |")
    
    lines.append("")
    
    return "\n".join(lines)


def main():
    spec_path = Path("openapi.json")
    output_path = Path("MEALIE_API_REFERENCE.md")
    
    print(f"Loading OpenAPI spec from {spec_path}...")
    spec = load_openapi_spec(spec_path)
    
    print("Extracting endpoints...")
    endpoints = extract_endpoints(spec)
    print(f"Found {len(endpoints)} endpoints")
    
    print("Categorizing endpoints...")
    categories = categorize_endpoints(endpoints)
    print(f"Found {len(categories)} categories")
    
    print("Generating markdown document...")
    markdown = generate_markdown(spec, endpoints, categories)
    
    print(f"Writing to {output_path}...")
    with open(output_path, "w") as f:
        f.write(markdown)
    
    print("Done!")
    
    # Print summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    for tag, eps in sorted(categories.items(), key=lambda x: -len(x[1])):
        print(f"  {tag}: {len(eps)} endpoints")


if __name__ == "__main__":
    main()
