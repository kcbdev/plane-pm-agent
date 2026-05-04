"""HTTP mode entry point for plane-pm-agent."""
import sys
import uvicorn
from app import mcp

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "http"
    if mode == "http":
        uvicorn.run(mcp.http_app(), host="0.0.0.0", port=8212, log_level="info")
    else:
        print(f"Unknown mode: {mode}", file=sys.stderr)
        sys.exit(1)