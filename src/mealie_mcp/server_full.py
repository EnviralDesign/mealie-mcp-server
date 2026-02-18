"""Full-profile Mealie MCP entrypoint with all available tools."""

import os
import sys
from pathlib import Path

# Ensure `mealie_mcp` is importable when this file is launched directly.
SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

os.environ["MEALIE_MCP_PROFILE"] = "full"

from mealie_mcp.server import mcp


if __name__ == "__main__":
    mcp.run()
