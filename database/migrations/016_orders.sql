-- 016_orders.sql
-- Order tracking for execution pipeline.

CREATE TYPE order_state_type AS ENUM (
  'submitted', 'pending', 'filled', 'partially_filled',
  'rejected', 'expired', 'cancelled'
);

CREATE TABLE orders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ticker TEXT NOT NULL,
  side TEXT NOT NULL CHECK (side IN ('buy', 'sell')),
  quantity INT NOT NULL CHECK (quantity > 0),
  price NUMERIC(12,4) NOT NULL,
  state order_state_type NOT NULL DEFAULT 'submitted',
  alpaca_order_id TEXT,
  fill_price NUMERIC(12,4),
  filled_quantity INT DEFAULT 0,
  slippage NUMERIC(10,4),
  risk_check_result JSONB DEFAULT '{}',
  pre_trade_result JSONB DEFAULT '{}',
  state_history JSONB DEFAULT '[]',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_orders_ticker ON orders(ticker);
CREATE INDEX idx_orders_state ON orders(state);
CREATE INDEX idx_orders_created ON orders(created_at DESC);
