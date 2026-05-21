<div align="center">

> ## 🧱 Part of the MEOK A2A Substrate
>
> This MCP is 1 of 12 agent-to-agent primitives. Run the whole pipeline
> (identity → trust → policy → firewall → rate-limit → handoff → audit
> → governance) as one signed endpoint for **£499/mo** including 100K
> calls — or **£0.0002 per call** pay-as-you-go.
>
> 👉 [meok.ai/a2a](https://meok.ai/a2a) — see the Substrate

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



## Multi-protocol agent payment support

This MCP is the **single bridge** between your agents and the three live agent-payments
protocols. Pick the one your buyer wants; the signed attestation chain stays the same.

| Protocol | Owner | When to use | Tool in this MCP |
|---|---|---|---|
| **Stripe ACP** (Agentic Commerce Protocol) | Stripe + OpenAI · Apache 2.0 | B2C agent purchases inside ChatGPT / merchant flows | `create_invoice` + `process_payment` with `protocol="stripe-acp"` |
| **AP2** (Agent Payments Protocol) | Google + Mastercard + PayPal + Adyen (60+ orgs) | Cross-platform regulated payments, B2B, cross-border | `process_payment` with `protocol="ap2"` — generates signed user mandate |
| **x402** | Coinbase | HTTP-native pay-per-call, micro-transactions, on-chain | `process_payment` with `protocol="x402"` — returns 402 + settlement instructions |
| **PSD2 / MiCA** | EU regulation | EU regulatory compliance overlay on any protocol | Automatic — applied to every transaction in EU jurisdiction |

> **Note on "ACP":** there are two protocols with this acronym. **IBM ACP** (Agent Communication
> Protocol) merged into A2A under Linux Foundation in September 2025 and is covered by the rest
> of the [MEOK A2A Substrate](https://meok.ai/a2a). **Stripe ACP** (Agentic Commerce Protocol)
> is the live payments protocol covered by this MCP.

### Why this MCP exists

The agent-payments space has three live protocols and none is dominant. Building against
just one means your agent commerce can't reach the other 2/3 of the market. This MCP wraps
all three behind one tool surface so your agent code stays portable.

Every transaction emits a hash-chained attestation to the [`agent-audit-logger-mcp`](https://github.com/CSOAI-ORG/agent-audit-logger-mcp)
sibling, giving you EU AI Act Article 12 + DORA Article 17 audit evidence for every payment.

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

<!-- meok-moat-footer-v1 -->
---

## Pairs with MEOK Governance Suite

Build something that touches users? You need compliance. MEOK ships 38 governance MCPs that drop in alongside this tool — EU AI Act, DORA, NIS2, CRA, GDPR, ISO 42001, FDA SaMD, MDR, Basel, MiFID II, MiCA, COPPA, and more.

```bash
# One-shot install of the governance pack
npx meok-setup --pack governance
```

Free tier: 10 calls/day per MCP. Pro tier (£79/mo): unlimited + cryptographically signed compliance attestations your auditor verifies independently.

→ Full catalogue: [councilof.ai/catalogue](https://councilof.ai/catalogue)
→ MEOK AI Labs: [meok.ai](https://meok.ai)

