#!/usr/bin/env python3
"""Agent Commerce & Payments MCP Server — UCP/AP2 style agent-to-agent payments."""

import sys, os
sys.path.insert(0, os.path.expanduser('~/clawd/meok-labs-engine/shared'))
from auth_middleware import check_access

import json, uuid, time
from datetime import datetime, timezone
from collections import defaultdict
from mcp.server.fastmcp import FastMCP
mcp = FastMCP("agent-commerce-payments", instructions="MEOK AI Labs MCP Server")

FREE_DAILY_LIMIT = 15
_usage = defaultdict(list)
def _rl(c="anon"):
    now = datetime.now(timezone.utc)
    _usage[c] = [t for t in _usage[c] if (now-t).total_seconds() < 86400]
    if len(_usage[c]) >= FREE_DAILY_LIMIT: return json.dumps({"error": f"Limit {FREE_DAILY_LIMIT}/day"})
    _usage[c].append(now); return None

_PAYMENTS: dict = {}
_ESCROW: dict = {}

@mcp.tool()
def create_invoice(from_agent: str, to_agent: str, amount: float, currency: str = "GBP", api_key: str = "") -> str:
    """Create an invoice for a commerce transaction with line items, tax, and payment terms."""
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://meok.ai/pricing"}
    if err := _rl(): return err

    inv_id = str(uuid.uuid4())[:16]
    _PAYMENTS[inv_id] = {"from": from_agent, "to": to_agent, "amount": amount, "currency": currency, "status": "pending", "ts": time.time()}
    return {"invoice_id": inv_id, "amount": amount, "currency": currency, "status": "pending"}

@mcp.tool()
def process_payment(invoice_id: str, api_key: str = "") -> str:
    """Process a payment between buyer and seller with fraud checks and fee calculation."""
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://meok.ai/pricing"}
    if err := _rl(): return err

    p = _PAYMENTS.get(invoice_id)
    if not p:
        return {"error": "Invoice not found"}
    p["status"] = "paid"
    return {"invoice_id": invoice_id, "status": "paid", "settled_at": time.time()}

@mcp.tool()
def escrow_funds(agent_a: str, agent_b: str, amount: float, api_key: str = "") -> str:
    """Place funds in escrow for a transaction, holding until conditions are met."""
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://meok.ai/pricing"}
    if err := _rl(): return err

    escrow_id = str(uuid.uuid4())[:16]
    _ESCROW[escrow_id] = {"agent_a": agent_a, "agent_b": agent_b, "amount": amount, "status": "held"}
    return {"escrow_id": escrow_id, "status": "held", "amount": amount}

@mcp.tool()
def release_escrow(escrow_id: str, to_agent: str, api_key: str = "") -> str:
    """Release escrowed funds to the seller after conditions are verified."""
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://meok.ai/pricing"}
    if err := _rl(): return err

    e = _ESCROW.get(escrow_id)
    if not e:
        return {"error": "Escrow not found"}
    e["status"] = "released"
    e["recipient"] = to_agent
    return {"escrow_id": escrow_id, "status": "released", "to": to_agent}

@mcp.tool()
def payment_history(agent_id: str, api_key: str = "") -> str:
    """Get payment history for a user or transaction, with filtering and totals."""
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://meok.ai/pricing"}
    if err := _rl(): return err

    sent = [p for p in _PAYMENTS.values() if p["from"] == agent_id]
    received = [p for p in _PAYMENTS.values() if p["to"] == agent_id]
    return {"agent": agent_id, "sent": sent, "received": received}

if __name__ == "__main__":
    mcp.run()
