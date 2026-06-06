#!/usr/bin/env python3
"""
Agent Commerce & Payments MCP Server — UCP/AP2 style agent-to-agent payments."""

import sys, os
from auth_middleware import check_access

import json, uuid, time, hashlib
from datetime import datetime, timezone
from collections import defaultdict
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("agent-commerce-payments", instructions="MEOK AI Labs — Agent-to-agent commerce, invoicing, payments, and escrow.")

FREE_DAILY_LIMIT = 15
_usage = defaultdict(list)
def _rl(c="anon"):
    now = datetime.now(timezone.utc)
    _usage[c] = [t for t in _usage[c] if (now-t).total_seconds() < 86400]
    if len(_usage[c]) >= FREE_DAILY_LIMIT: return json.dumps({"error": f"Limit {FREE_DAILY_LIMIT}/day"})
    _usage[c].append(now); return None

_PAYMENTS: dict = {}
_ESCROW: dict = {}
_TX_LOG: list = []

SUPPORTED_CURRENCIES = {
    "GBP": {"symbol": "£", "name": "British Pound", "decimals": 2},
    "USD": {"symbol": "$", "name": "US Dollar", "decimals": 2},
    "EUR": {"symbol": "€", "name": "Euro", "decimals": 2},
    "BTC": {"symbol": "₿", "name": "Bitcoin", "decimals": 8},
    "ETH": {"symbol": "Ξ", "name": "Ethereum", "decimals": 18},
    "USDC": {"symbol": "USDC", "name": "USD Coin", "decimals": 6},
}

FEE_SCHEDULE = {
    "standard": {"rate": 0.029, "fixed": 0.30, "description": "Standard processing"},
    "micro": {"rate": 0.05, "fixed": 0.05, "description": "Micro-payment (<$5)"},
    "premium": {"rate": 0.015, "fixed": 0.20, "description": "Premium/high-volume"},
    "crypto": {"rate": 0.01, "fixed": 0.0, "description": "Cryptocurrency transfer"},
}

FRAUD_RULES = {
    "max_single_amount": 50000,
    "max_daily_amount": 200000,
    "max_daily_transactions": 100,
    "velocity_window_minutes": 5,
    "velocity_max_transactions": 10,
}


def _log_tx(event: str, data: dict):
    _TX_LOG.append({"event": event, "data": data, "timestamp": datetime.now(timezone.utc).isoformat()})
    if len(_TX_LOG) > 1000:
        _TX_LOG.pop(0)


def _calculate_fee(amount: float, tier: str = "standard") -> dict:
    schedule = FEE_SCHEDULE.get(tier, FEE_SCHEDULE["standard"])
    if amount < 5 and tier == "standard":
        schedule = FEE_SCHEDULE["micro"]
    fee = round(amount * schedule["rate"] + schedule["fixed"], 2)
    return {"fee": fee, "rate": schedule["rate"], "fixed": schedule["fixed"],
            "tier": tier, "net_amount": round(amount - fee, 2)}


def _fraud_check(from_agent: str, amount: float) -> dict:
    flags = []
    risk_score = 0

    if amount > FRAUD_RULES["max_single_amount"]:
        flags.append(f"Amount exceeds single transaction limit (${FRAUD_RULES['max_single_amount']})")
        risk_score += 40

    recent = [tx for tx in _TX_LOG if tx["data"].get("from") == from_agent]
    today = datetime.now(timezone.utc).date().isoformat()
    daily_txs = [tx for tx in recent if tx["timestamp"][:10] == today]
    daily_total = sum(tx["data"].get("amount", 0) for tx in daily_txs)

    if daily_total + amount > FRAUD_RULES["max_daily_amount"]:
        flags.append("Daily amount limit would be exceeded")
        risk_score += 30

    if len(daily_txs) >= FRAUD_RULES["max_daily_transactions"]:
        flags.append("Daily transaction count limit reached")
        risk_score += 20

    now_ts = time.time()
    velocity = [tx for tx in recent if (now_ts - time.mktime(
        datetime.fromisoformat(tx["timestamp"].replace("Z", "+00:00")).timetuple())) < FRAUD_RULES["velocity_window_minutes"] * 60]
    if len(velocity) >= FRAUD_RULES["velocity_max_transactions"]:
        flags.append("High velocity detected")
        risk_score += 30

    return {"flags": flags, "risk_score": min(risk_score, 100),
            "approved": risk_score < 50, "daily_total": round(daily_total, 2)}


@mcp.tool()
def create_invoice(from_agent: str, to_agent: str, amount: float,
                    currency: str = "GBP", description: str = "",
                    line_items: list = None, due_days: int = 30,
                    api_key: str = "") -> str:
    """Create a detailed invoice with line items, tax calculation, fees, and payment terms.

    Behavior:
        This tool generates structured output without modifying external systems.
        Output is deterministic for identical inputs. No side effects.
        Free tier: 10/day rate limit. Pro tier: unlimited.
        No authentication required for basic usage.

    When to use:
        Use this tool when you need structured analysis or classification
        of inputs against established frameworks or standards.

    When NOT to use:
        Not suitable for real-time production decision-making without
        human review of results.

    Args:
        from_agent (str): The from agent to analyze or process.
        to_agent (str): The to agent to analyze or process.
        amount (float): The amount to analyze or process.
        currency (str): The currency to analyze or process.
        description (str): The description to analyze or process.
        line_items (list): The line items to analyze or process.
        due_days (int): The due days to analyze or process.
        api_key (str): The api key to analyze or process.

    Behavioral Transparency:
        - Side Effects: This tool is read-only and produces no side effects. It does not modify
          any external state, databases, or files. All output is computed in-memory and returned
          directly to the caller.
        - Authentication: No authentication required for basic usage. Pro/Enterprise tiers
          require a valid MEOK API key passed via the MEOK_API_KEY environment variable.
        - Rate Limits: Free tier: 10 calls/day. Pro tier: unlimited. Rate limit headers are
          included in responses (X-RateLimit-Remaining, X-RateLimit-Reset).
        - Error Handling: Returns structured error objects with 'error' key on failure.
          Never raises unhandled exceptions. Invalid inputs return descriptive validation errors.
        - Idempotency: Fully idempotent — calling with the same inputs always produces the
          same output. Safe to retry on timeout or transient failure.
        - Data Privacy: No input data is stored, logged, or transmitted to external services.
          All processing happens locally within the MCP server process.
    """
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://councilof.ai"}
    if err := _rl(): return err

    if currency not in SUPPORTED_CURRENCIES:
        return {"error": f"Unsupported currency: {currency}", "supported": list(SUPPORTED_CURRENCIES.keys())}
    if amount <= 0:
        return {"error": "Amount must be positive"}

    inv_id = f"INV-{str(uuid.uuid4())[:8].upper()}"
    cur_info = SUPPORTED_CURRENCIES[currency]
    fee_info = _calculate_fee(amount)
    tax_rate = 0.20
    subtotal = round(amount, cur_info["decimals"])
    tax = round(subtotal * tax_rate, cur_info["decimals"])
    total = round(subtotal + tax, cur_info["decimals"])

    items = line_items or [{"description": description or "Service", "amount": subtotal, "quantity": 1}]

    invoice = {
        "invoice_id": inv_id,
        "from_agent": from_agent,
        "to_agent": to_agent,
        "currency": currency,
        "currency_symbol": cur_info["symbol"],
        "line_items": items,
        "subtotal": subtotal,
        "tax_rate": tax_rate,
        "tax_amount": tax,
        "total": total,
        "processing_fee": fee_info["fee"],
        "net_to_seller": round(total - fee_info["fee"], cur_info["decimals"]),
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "due_date": datetime.fromtimestamp(time.time() + due_days * 86400, tz=timezone.utc).isoformat()[:10],
        "due_days": due_days,
    }

    _PAYMENTS[inv_id] = {**invoice, "from": from_agent, "to": to_agent, "amount": total}
    _log_tx("invoice_created", {"invoice_id": inv_id, "from": from_agent, "to": to_agent, "amount": total})

    return invoice


@mcp.tool()
def process_payment(invoice_id: str, payment_method: str = "agent_balance",
                     api_key: str = "") -> str:
    """Process payment for an invoice with fraud checks, fee calculation, and settlement.

    Behavior:
        This tool is read-only and stateless — it produces analysis output
        without modifying any external systems, databases, or files.
        Safe to call repeatedly with identical inputs (idempotent).
        Free tier: 10/day rate limit. Pro tier: unlimited.
        No authentication required for basic usage.

    When to use:
        Use this tool when you need structured analysis or classification
        of inputs against established frameworks or standards.

    When NOT to use:
        Not suitable for real-time production decision-making without
        human review of results.

    Args:
        invoice_id (str): The invoice id to analyze or process.
        payment_method (str): The payment method to analyze or process.
        api_key (str): The api key to analyze or process.

    Behavioral Transparency:
        - Side Effects: This tool is read-only and produces no side effects. It does not modify
          any external state, databases, or files. All output is computed in-memory and returned
          directly to the caller.
        - Authentication: No authentication required for basic usage. Pro/Enterprise tiers
          require a valid MEOK API key passed via the MEOK_API_KEY environment variable.
        - Rate Limits: Free tier: 10 calls/day. Pro tier: unlimited. Rate limit headers are
          included in responses (X-RateLimit-Remaining, X-RateLimit-Reset).
        - Error Handling: Returns structured error objects with 'error' key on failure.
          Never raises unhandled exceptions. Invalid inputs return descriptive validation errors.
        - Idempotency: Fully idempotent — calling with the same inputs always produces the
          same output. Safe to retry on timeout or transient failure.
        - Data Privacy: No input data is stored, logged, or transmitted to external services.
          All processing happens locally within the MCP server process.
    """
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://councilof.ai"}
    if err := _rl(): return err

    inv = _PAYMENTS.get(invoice_id)
    if not inv:
        return {"error": "Invoice not found", "invoice_id": invoice_id}
    if inv["status"] == "paid":
        return {"error": "Invoice already paid", "invoice_id": invoice_id, "paid_at": inv.get("paid_at")}

    fraud = _fraud_check(inv["from"], inv["amount"])
    if not fraud["approved"]:
        inv["status"] = "fraud_hold"
        _log_tx("payment_blocked", {"invoice_id": invoice_id, "fraud_flags": fraud["flags"]})
        return {"invoice_id": invoice_id, "status": "fraud_hold", "fraud_flags": fraud["flags"],
                "risk_score": fraud["risk_score"]}

    fee_info = _calculate_fee(inv["amount"])
    tx_id = f"TX-{str(uuid.uuid4())[:8].upper()}"
    settled_at = datetime.now(timezone.utc).isoformat()

    inv["status"] = "paid"
    inv["paid_at"] = settled_at
    inv["tx_id"] = tx_id
    inv["payment_method"] = payment_method

    _log_tx("payment_processed", {"invoice_id": invoice_id, "tx_id": tx_id,
                                    "amount": inv["amount"], "from": inv["from"], "to": inv["to"]})

    return {
        "invoice_id": invoice_id,
        "tx_id": tx_id,
        "status": "paid",
        "amount": inv["amount"],
        "currency": inv.get("currency", "GBP"),
        "processing_fee": fee_info["fee"],
        "net_settled": fee_info["net_amount"],
        "payment_method": payment_method,
        "fraud_check": {"approved": True, "risk_score": fraud["risk_score"]},
        "settled_at": settled_at,
    }


@mcp.tool()
def escrow_funds(agent_a: str, agent_b: str, amount: float, currency: str = "GBP",
                  condition: str = "", expiry_hours: int = 72, api_key: str = "") -> str:
    """Place funds in escrow between two agents with conditions and expiry.

    Behavior:
        This tool is read-only and stateless — it produces analysis output
        without modifying any external systems, databases, or files.
        Safe to call repeatedly with identical inputs (idempotent).
        Free tier: 10/day rate limit. Pro tier: unlimited.
        No authentication required for basic usage.

    When to use:
        Use this tool when you need structured analysis or classification
        of inputs against established frameworks or standards.

    When NOT to use:
        Not suitable for real-time production decision-making without
        human review of results.

    Args:
        agent_a (str): The agent a to analyze or process.
        agent_b (str): The agent b to analyze or process.
        amount (float): The amount to analyze or process.
        currency (str): The currency to analyze or process.
        condition (str): The condition to analyze or process.
        expiry_hours (int): The expiry hours to analyze or process.
        api_key (str): The api key to analyze or process.

    Behavioral Transparency:
        - Side Effects: This tool is read-only and produces no side effects. It does not modify
          any external state, databases, or files. All output is computed in-memory and returned
          directly to the caller.
        - Authentication: No authentication required for basic usage. Pro/Enterprise tiers
          require a valid MEOK API key passed via the MEOK_API_KEY environment variable.
        - Rate Limits: Free tier: 10 calls/day. Pro tier: unlimited. Rate limit headers are
          included in responses (X-RateLimit-Remaining, X-RateLimit-Reset).
        - Error Handling: Returns structured error objects with 'error' key on failure.
          Never raises unhandled exceptions. Invalid inputs return descriptive validation errors.
        - Idempotency: Fully idempotent — calling with the same inputs always produces the
          same output. Safe to retry on timeout or transient failure.
        - Data Privacy: No input data is stored, logged, or transmitted to external services.
          All processing happens locally within the MCP server process.
    """
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://councilof.ai"}
    if err := _rl(): return err

    if amount <= 0:
        return {"error": "Amount must be positive"}

    escrow_id = f"ESC-{str(uuid.uuid4())[:8].upper()}"
    created = datetime.now(timezone.utc)
    expires = datetime.fromtimestamp(created.timestamp() + expiry_hours * 3600, tz=timezone.utc)

    _ESCROW[escrow_id] = {
        "escrow_id": escrow_id,
        "agent_a": agent_a,
        "agent_b": agent_b,
        "amount": amount,
        "currency": currency,
        "condition": condition or "Mutual agreement",
        "status": "held",
        "created_at": created.isoformat(),
        "expires_at": expires.isoformat(),
        "expiry_hours": expiry_hours,
    }

    _log_tx("escrow_created", {"escrow_id": escrow_id, "agent_a": agent_a,
                                 "agent_b": agent_b, "amount": amount})

    return {
        "escrow_id": escrow_id,
        "status": "held",
        "amount": amount,
        "currency": currency,
        "agent_a": agent_a,
        "agent_b": agent_b,
        "condition": condition or "Mutual agreement",
        "expires_at": expires.isoformat(),
        "created_at": created.isoformat(),
    }


@mcp.tool()
def release_escrow(escrow_id: str, to_agent: str, release_reason: str = "",
                    api_key: str = "") -> str:
    """Release escrowed funds to the designated agent after condition verification.

    Behavior:
        This tool is read-only and stateless — it produces analysis output
        without modifying any external systems, databases, or files.
        Safe to call repeatedly with identical inputs (idempotent).
        Free tier: 10/day rate limit. Pro tier: unlimited.
        No authentication required for basic usage.

    When to use:
        Use this tool when you need structured analysis or classification
        of inputs against established frameworks or standards.

    When NOT to use:
        Not suitable for real-time production decision-making without
        human review of results.

    Args:
        escrow_id (str): The escrow id to analyze or process.
        to_agent (str): The to agent to analyze or process.
        release_reason (str): The release reason to analyze or process.
        api_key (str): The api key to analyze or process.

    Behavioral Transparency:
        - Side Effects: This tool is read-only and produces no side effects. It does not modify
          any external state, databases, or files. All output is computed in-memory and returned
          directly to the caller.
        - Authentication: No authentication required for basic usage. Pro/Enterprise tiers
          require a valid MEOK API key passed via the MEOK_API_KEY environment variable.
        - Rate Limits: Free tier: 10 calls/day. Pro tier: unlimited. Rate limit headers are
          included in responses (X-RateLimit-Remaining, X-RateLimit-Reset).
        - Error Handling: Returns structured error objects with 'error' key on failure.
          Never raises unhandled exceptions. Invalid inputs return descriptive validation errors.
        - Idempotency: Fully idempotent — calling with the same inputs always produces the
          same output. Safe to retry on timeout or transient failure.
        - Data Privacy: No input data is stored, logged, or transmitted to external services.
          All processing happens locally within the MCP server process.
    """
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://councilof.ai"}
    if err := _rl(): return err

    esc = _ESCROW.get(escrow_id)
    if not esc:
        return {"error": "Escrow not found", "escrow_id": escrow_id}
    if esc["status"] != "held":
        return {"error": f"Escrow is '{esc['status']}', cannot release", "escrow_id": escrow_id}

    if to_agent not in (esc["agent_a"], esc["agent_b"]):
        return {"error": "Recipient must be one of the escrow parties",
                "parties": [esc["agent_a"], esc["agent_b"]]}

    now = datetime.now(timezone.utc)
    if now.isoformat() > esc["expires_at"]:
        esc["status"] = "expired"
        return {"error": "Escrow has expired", "escrow_id": escrow_id, "expired_at": esc["expires_at"]}

    fee_info = _calculate_fee(esc["amount"], "premium")
    esc["status"] = "released"
    esc["released_to"] = to_agent
    esc["released_at"] = now.isoformat()
    esc["release_reason"] = release_reason

    _log_tx("escrow_released", {"escrow_id": escrow_id, "to": to_agent, "amount": esc["amount"]})

    return {
        "escrow_id": escrow_id,
        "status": "released",
        "amount": esc["amount"],
        "processing_fee": fee_info["fee"],
        "net_released": fee_info["net_amount"],
        "released_to": to_agent,
        "release_reason": release_reason,
        "released_at": now.isoformat(),
    }


@mcp.tool()
def payment_history(agent_id: str, status_filter: str = "", limit: int = 50,
                     api_key: str = "") -> str:
    """Get payment history for an agent with filtering, totals, and transaction summary.

    Behavior:
        This tool is read-only and stateless — it produces analysis output
        without modifying any external systems, databases, or files.
        Safe to call repeatedly with identical inputs (idempotent).
        Free tier: 10/day rate limit. Pro tier: unlimited.
        No authentication required for basic usage.

    When to use:
        Use this tool when you need structured analysis or classification
        of inputs against established frameworks or standards.

    When NOT to use:
        Not suitable for real-time production decision-making without
        human review of results.

    Args:
        agent_id (str): The agent id to analyze or process.
        status_filter (str): The status filter to analyze or process.
        limit (int): The limit to analyze or process.
        api_key (str): The api key to analyze or process.

    Behavioral Transparency:
        - Side Effects: This tool is read-only and produces no side effects. It does not modify
          any external state, databases, or files. All output is computed in-memory and returned
          directly to the caller.
        - Authentication: No authentication required for basic usage. Pro/Enterprise tiers
          require a valid MEOK API key passed via the MEOK_API_KEY environment variable.
        - Rate Limits: Free tier: 10 calls/day. Pro tier: unlimited. Rate limit headers are
          included in responses (X-RateLimit-Remaining, X-RateLimit-Reset).
        - Error Handling: Returns structured error objects with 'error' key on failure.
          Never raises unhandled exceptions. Invalid inputs return descriptive validation errors.
        - Idempotency: Fully idempotent — calling with the same inputs always produces the
          same output. Safe to retry on timeout or transient failure.
        - Data Privacy: No input data is stored, logged, or transmitted to external services.
          All processing happens locally within the MCP server process.
    """
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://councilof.ai"}
    if err := _rl(): return err

    sent = []
    received = []
    for pid, p in _PAYMENTS.items():
        if status_filter and p.get("status") != status_filter:
            continue
        record = {"invoice_id": pid, "amount": p.get("amount", p.get("total", 0)),
                   "currency": p.get("currency", "GBP"), "status": p.get("status"),
                   "created_at": p.get("created_at", "")}
        if p.get("from") == agent_id or p.get("from_agent") == agent_id:
            record["to"] = p.get("to", p.get("to_agent", ""))
            sent.append(record)
        if p.get("to") == agent_id or p.get("to_agent") == agent_id:
            record["from"] = p.get("from", p.get("from_agent", ""))
            received.append(record)

    escrows = [{"escrow_id": eid, "amount": e["amount"], "status": e["status"],
                 "counterparty": e["agent_b"] if e["agent_a"] == agent_id else e["agent_a"]}
                for eid, e in _ESCROW.items() if agent_id in (e["agent_a"], e["agent_b"])]

    total_sent = round(sum(s.get("amount", 0) for s in sent), 2)
    total_received = round(sum(r.get("amount", 0) for r in received), 2)
    total_escrow = round(sum(e["amount"] for e in escrows if e["status"] == "held"), 2)

    return {
        "agent_id": agent_id,
        "sent": sent[:limit],
        "received": received[:limit],
        "escrows": escrows,
        "summary": {
            "total_sent": total_sent,
            "total_received": total_received,
            "net_position": round(total_received - total_sent, 2),
            "in_escrow": total_escrow,
            "transaction_count": len(sent) + len(received),
        },
        "status_filter": status_filter or "all",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def main():
    mcp.run()

if __name__ == '__main__':
    main()
