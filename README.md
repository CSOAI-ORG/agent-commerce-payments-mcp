# Agent Commerce Payments MCP Server

> By [MEOK AI Labs](https://meok.ai) — Agent-to-agent commerce payments, invoicing, and escrow

## Installation

```bash
pip install agent-commerce-payments-mcp
```

## Usage

```bash
# Run standalone
python server.py

# Or via MCP
mcp install agent-commerce-payments-mcp
```

## Tools

### `create_invoice`
Create an invoice for a commerce transaction with line items, tax, and payment terms.

**Parameters:**
- `from_agent` (str): Sending agent identifier
- `to_agent` (str): Receiving agent identifier
- `amount` (float): Invoice amount
- `currency` (str): Currency code (default 'GBP')

### `process_payment`
Process a payment between buyer and seller with fraud checks and fee calculation.

**Parameters:**
- `invoice_id` (str): Invoice to process

### `escrow_funds`
Place funds in escrow for a transaction, holding until conditions are met.

**Parameters:**
- `agent_a` (str): First agent
- `agent_b` (str): Second agent
- `amount` (float): Amount to escrow

### `release_escrow`
Release escrowed funds to the seller after conditions are verified.

**Parameters:**
- `escrow_id` (str): Escrow identifier
- `to_agent` (str): Recipient agent

### `payment_history`
Get payment history for a user or transaction, with filtering and totals.

**Parameters:**
- `agent_id` (str): Agent identifier

## Authentication

Free tier: 15 calls/day. Upgrade at [meok.ai/pricing](https://meok.ai/pricing) for unlimited access.

## License

MIT — MEOK AI Labs
