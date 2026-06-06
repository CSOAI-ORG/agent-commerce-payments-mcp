#!/usr/bin/env python3
import sys
import os
import json
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
_shared_auth = os.path.expanduser("~/clawd/meok-labs-engine/shared")
if os.path.isdir(_shared_auth):
    sys.path.insert(0, _shared_auth)


import server

# Bypass shared auth rate limiting for tests
server.check_access = lambda api_key="": (True, "test", "pro")


def test_server_module_imports():
    assert server is not None


def test_mcp_object_exists():
    import server
    assert hasattr(server, "mcp")


def test_tools_registered():
    import server
    expected = [
        "create_invoice",
        "process_payment",
        "escrow_funds",
        "release_escrow",
        "payment_history",
    ]
    for name in expected:
        assert hasattr(server, name), f"Missing tool: {name}"
        assert callable(getattr(server, name))


def test_main_function():
    import server
    assert hasattr(server, "main")
    assert callable(server.main)


def test_create_invoice():
    import server
    result = server.create_invoice(
        from_agent="agent-alpha",
        to_agent="agent-beta",
        amount=100.0,
        currency="GBP",
        description="Consulting services",
    )
    assert isinstance(result, dict)
    assert result.get("invoice_id", "").startswith("INV-")
    assert result["from_agent"] == "agent-alpha"
    assert result["to_agent"] == "agent-beta"
    assert result["currency"] == "GBP"
    assert result["total"] > 0
    assert result["status"] == "pending"


def test_create_invoice_with_line_items():
    import server
    result = server.create_invoice(
        from_agent="a",
        to_agent="b",
        amount=250.0,
        line_items=[
            {"description": "Setup fee", "amount": 100, "quantity": 1},
            {"description": "Monthly subscription", "amount": 150, "quantity": 1},
        ],
    )
    assert isinstance(result, dict)
    assert "invoice_id" in result


def test_create_invoice_invalid_currency():
    import server
    result = server.create_invoice(
        from_agent="a",
        to_agent="b",
        amount=50,
        currency="XYZ",
    )
    assert isinstance(result, dict)
    assert "error" in result


def test_create_invoice_negative_amount():
    import server
    result = server.create_invoice(
        from_agent="a",
        to_agent="b",
        amount=-10,
    )
    assert isinstance(result, dict)
    assert "error" in result


def test_process_payment_not_found():
    import server
    result = server.process_payment(invoice_id="INV-NONEXISTENT")
    assert isinstance(result, dict)
    assert "error" in result
    assert "Invoice not found" in str(result)


def test_create_invoice_then_process_payment():
    import server
    inv = server.create_invoice(
        from_agent="agent-pay",
        to_agent="agent-collect",
        amount=50.0,
    )
    invoice_id = inv["invoice_id"]
    result = server.process_payment(invoice_id=invoice_id)
    assert isinstance(result, dict)
    assert result.get("status") == "paid"
    assert "tx_id" in result


def test_escrow_funds():
    import server
    result = server.escrow_funds(
        agent_a="agent-alpha",
        agent_b="agent-beta",
        amount=500.0,
        condition="Service delivery confirmed",
    )
    assert isinstance(result, dict)
    assert result.get("escrow_id", "").startswith("ESC-")
    assert result["status"] == "held"
    assert result["amount"] == 500.0


def test_release_escrow_not_found():
    import server
    result = server.release_escrow(
        escrow_id="ESC-NONEXISTENT",
        to_agent="agent-alpha",
    )
    assert isinstance(result, dict)
    assert "error" in result


def test_escrow_full_flow():
    import server
    escrow = server.escrow_funds(
        agent_a="alice",
        agent_b="bob",
        amount=100.0,
    )
    escrow_id = escrow["escrow_id"]
    result = server.release_escrow(
        escrow_id=escrow_id,
        to_agent="bob",
        release_reason="Work completed",
    )
    assert isinstance(result, dict)
    assert result["status"] == "released"
    assert result["released_to"] == "bob"


def test_payment_history():
    import server
    result = server.payment_history(agent_id="agent-alpha")
    assert isinstance(result, dict)
    assert "agent_id" in result
    assert "summary" in result
    assert result["agent_id"] == "agent-alpha"
