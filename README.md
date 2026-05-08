<div align="center">

# Agent Commerce Payments MCP

**MCP server for agent commerce payments mcp operations**

[![PyPI](https://img.shields.io/pypi/v/meok-agent-commerce-payments-mcp)](https://pypi.org/project/meok-agent-commerce-payments-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![MEOK AI Labs](https://img.shields.io/badge/MEOK_AI_Labs-MCP_Server-purple)](https://meok.ai)

</div>

## Overview

Agent Commerce Payments MCP provides AI-powered tools via the Model Context Protocol (MCP).

## Tools

| Tool | Description |
|------|-------------|
| `create_invoice` | Create a detailed invoice with line items, tax calculation, fees, and payment te |
| `process_payment` | Process payment for an invoice with fraud checks, fee calculation, and settlemen |
| `escrow_funds` | Place funds in escrow between two agents with conditions and expiry. |
| `release_escrow` | Release escrowed funds to the designated agent after condition verification. |
| `payment_history` | Get payment history for an agent with filtering, totals, and transaction summary |

## Installation

```bash
pip install meok-agent-commerce-payments-mcp
```

## Usage with Claude Desktop

Add to your Claude Desktop MCP config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "agent-commerce-payments": {
      "command": "python",
      "args": ["-m", "meok_agent_commerce_payments_mcp.server"]
    }
  }
}
```

## Usage with FastMCP

```python
from mcp.server.fastmcp import FastMCP

# This server exposes 5 tool(s) via MCP
# See server.py for full implementation
```

## License

MIT © [MEOK AI Labs](https://meok.ai)
