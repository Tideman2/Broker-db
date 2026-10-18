# Plan Pool — Design

Date: 2026-10-18
Branch: `feat/plan-pool`

## Intent

Give every plan subscription its own funded **pool** so that:

- all trading happens under a subscription, and each trade records which
  subscription it belongs to;
- a plan's profit can be computed per subscription;
- uninvested plan money is held in the subscription's pool and returned
  to the user's available balance when the subscription closes.

## Data model

- `subscriptions.pool DECIMAL(20,8) NOT NULL DEFAULT 0` (migration 028).
- `transactions.subscription_id` already exists (nullable FK) — start
  populating it. No backfill of existing rows.
- Subscribe no longer calls `_lock_funds`; `wallet.locked` returns to
  being withdrawal-only.

## Money rules

- **Subscribe:** `available -= amount`, `pool += amount`.
- **Buy (admin only):** request names `subscription_id`; validate the
  subscription belongs to the target user and is `ACTIVE`; require
  `pool >= cost` (else `400 {"detail": "Insufficient subscription pool."}`);
  `pool -= cost`; insert BUY with `subscription_id`.
- **Sell (admin only):** request names `subscription_id`; same
  ownership/active checks; the quantity is checked against the position
  held under that subscription (not the user's combined holdings, since
  each subscription has its own pool and open lots); `pool += proceeds`;
  insert SELL with `subscription_id`.
- **Cancel:** settles immediately (see below), status `CANCELLED`.
- **Expiry:** a 24h background sweep settles `ACTIVE` subscriptions whose
  `expiration_date <= now`, status `COMPLETED`.

### Settlement (shared routine)

1. For each instrument with open FIFO lots under the subscription, sell
   `remaining_quantity` at `instrument.current_price`; insert SELL
   transactions tagged with the subscription.
2. `available += pool`, `pool = 0`, set the final status.

Money is conserved: a 1000 plan that buys 500 and sells 300 ends with
`pool = 800` released to available and the user holding the position that
cost 200.

## Endpoints

- **Remove** `/portfolio/buy` and `/portfolio/sell` (no user-facing trading;
  a user with no active subscription cannot trade).
- `/portfolio/admin/buy/{user_id}` and `/portfolio/admin/sell/{user_id}`
  gain a required `subscription_id`.
- **Restore** `POST /subscription/cancel/{subscription_id}`
  (response model fixed; the pool dissolves the documented blocker 2).
- `SubscriptionResponse` gains `pool`.
- New `GET /subscription/summary` returns `list[SubscriptionSummaryResponse]`
  for the user's active subscriptions — reviving the currently unused
  `SubscriptionSummaryResponse` (`principal`, `current_value`,
  `profit_loss`, `roi_percent`, `status`) with `pool` added.

## Background job

A settlement service modeled on `EmailService`: a daemon thread started
and stopped in the FastAPI lifespan, running the expiry sweep every 24
hours. A module-level `run_expiry_sweep()` function performs one pass so
it is testable without waiting for the interval.

## Out of scope

- Backfilling existing subscriptions.
- Real-time price feeds (liquidation uses `instrument.current_price`).
