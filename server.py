#!/usr/bin/env python3
"""Agent Commerce & Payments MCP Server — UCP/AP2 style agent-to-agent payments."""
import json, uuid, time
from mcp.server.fastmcp import FastMCP
mcp = FastMCP("agent-commerce-payments-mcp")

_PAYMENTS: dict = {}
_ESCROW: dict = {}

@mcp.tool(name="create_invoice")
async def create_invoice(from_agent: str, to_agent: str, amount: float, currency: str = "GBP") -> str:
    inv_id = str(uuid.uuid4())[:16]
    _PAYMENTS[inv_id] = {"from": from_agent, "to": to_agent, "amount": amount, "currency": currency, "status": "pending", "ts": time.time()}
    return json.dumps({"invoice_id": inv_id, "amount": amount, "currency": currency, "status": "pending"})

@mcp.tool(name="process_payment")
async def process_payment(invoice_id: str) -> str:
    p = _PAYMENTS.get(invoice_id)
    if not p:
        return json.dumps({"error": "Invoice not found"})
    p["status"] = "paid"
    return json.dumps({"invoice_id": invoice_id, "status": "paid", "settled_at": time.time()})

@mcp.tool(name="escrow_funds")
async def escrow_funds(agent_a: str, agent_b: str, amount: float) -> str:
    escrow_id = str(uuid.uuid4())[:16]
    _ESCROW[escrow_id] = {"agent_a": agent_a, "agent_b": agent_b, "amount": amount, "status": "held"}
    return json.dumps({"escrow_id": escrow_id, "status": "held", "amount": amount})

@mcp.tool(name="release_escrow")
async def release_escrow(escrow_id: str, to_agent: str) -> str:
    e = _ESCROW.get(escrow_id)
    if not e:
        return json.dumps({"error": "Escrow not found"})
    e["status"] = "released"
    e["recipient"] = to_agent
    return json.dumps({"escrow_id": escrow_id, "status": "released", "to": to_agent})

@mcp.tool(name="payment_history")
async def payment_history(agent_id: str) -> str:
    sent = [p for p in _PAYMENTS.values() if p["from"] == agent_id]
    received = [p for p in _PAYMENTS.values() if p["to"] == agent_id]
    return json.dumps({"agent": agent_id, "sent": sent, "received": received})

if __name__ == "__main__":
    mcp.run()
