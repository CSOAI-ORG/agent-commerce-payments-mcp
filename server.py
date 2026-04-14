#!/usr/bin/env python3
"""Agent Commerce & Payments MCP Server — UCP/AP2 style agent-to-agent payments."""

import sys, os
sys.path.insert(0, os.path.expanduser('~/clawd/meok-labs-engine/shared'))
from auth_middleware import check_access

import json, uuid, time
from mcp.server.fastmcp import FastMCP
mcp = FastMCP("agent-commerce-payments-mcp")

_PAYMENTS: dict = {}
_ESCROW: dict = {}

@mcp.tool(name="create_invoice")
async def create_invoice(from_agent: str, to_agent: str, amount: float, currency: str = "GBP", api_key: str = "") -> str:
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://meok.ai/pricing"}

    inv_id = str(uuid.uuid4())[:16]
    _PAYMENTS[inv_id] = {"from": from_agent, "to": to_agent, "amount": amount, "currency": currency, "status": "pending", "ts": time.time()}
    return {"invoice_id": inv_id, "amount": amount, "currency": currency, "status": "pending"}

@mcp.tool(name="process_payment")
async def process_payment(invoice_id: str, api_key: str = "") -> str:
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://meok.ai/pricing"}

    p = _PAYMENTS.get(invoice_id)
    if not p:
        return {"error": "Invoice not found"}
    p["status"] = "paid"
    return {"invoice_id": invoice_id, "status": "paid", "settled_at": time.time()}

@mcp.tool(name="escrow_funds")
async def escrow_funds(agent_a: str, agent_b: str, amount: float, api_key: str = "") -> str:
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://meok.ai/pricing"}

    escrow_id = str(uuid.uuid4())[:16]
    _ESCROW[escrow_id] = {"agent_a": agent_a, "agent_b": agent_b, "amount": amount, "status": "held"}
    return {"escrow_id": escrow_id, "status": "held", "amount": amount}

@mcp.tool(name="release_escrow")
async def release_escrow(escrow_id: str, to_agent: str, api_key: str = "") -> str:
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://meok.ai/pricing"}

    e = _ESCROW.get(escrow_id)
    if not e:
        return {"error": "Escrow not found"}
    e["status"] = "released"
    e["recipient"] = to_agent
    return {"escrow_id": escrow_id, "status": "released", "to": to_agent}

@mcp.tool(name="payment_history")
async def payment_history(agent_id: str, api_key: str = "") -> str:
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://meok.ai/pricing"}

    sent = [p for p in _PAYMENTS.values() if p["from"] == agent_id]
    received = [p for p in _PAYMENTS.values() if p["to"] == agent_id]
    return {"agent": agent_id, "sent": sent, "received": received}

if __name__ == "__main__":
    mcp.run()
