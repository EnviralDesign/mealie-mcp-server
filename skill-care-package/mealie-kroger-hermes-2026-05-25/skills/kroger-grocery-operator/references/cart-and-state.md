# Cart And State

## Authentication

If the Kroger MCP reports it is unauthenticated, use its authentication flow. The server should provide an authorization URL; the human may need to complete login and paste the redirect URL back.

## Preferred Location

Verify current location before serious work:

- expected location id: `03500445`
- expected address: `5330 S Cooper St, Arlington, TX 76017`

If missing or wrong, set it again and verify the preference was written to persistent state.

## Persistent State

The deployed server should mount `KROGER_TOKEN_DIR` to persistent storage. Important files:

- `kroger_preferences.json` for preferred location,
- `kroger_cart.json` for local cart tracking,
- token files for auth.

If the container restarts and forgets the store, inspect the Unraid container volume/env setup.

## Cart Operations

Use cart tools cautiously:

- `add_items_to_cart` and `bulk_add_to_cart` may add to the real Kroger account cart.
- `view_current_cart` is local MCP tracking, not guaranteed to be Kroger's server-side cart.
- local remove/clear actions do not remove real items from the Kroger cart.
- `mark_order_placed` archives local tracking after the user places the order.

For ambiguous grocery requests, search and present candidates before adding.
