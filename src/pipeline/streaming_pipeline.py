"""Streaming decision pipeline — yields SSE events as each node executes.

Inherits from DecisionPipeline and reuses all _node_* methods. Zero logic
duplication — only adds async generator wrapper with event emission.
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone

from src.pipeline.decision_pipeline import DecisionPipeline
from src.pipeline.state import TradingState

logger = logging.getLogger("wasden_watch.pipeline.streaming")

# Ordered list of all 10 pipeline nodes
PIPELINE_NODES = [
    {"name": "quant_scoring", "label": "Quant Scoring", "index": 0},
    {"name": "wasden_watch", "label": "Wasden Watch", "index": 1},
    {"name": "bull_researcher", "label": "Bull Researcher", "index": 2},
    {"name": "bear_researcher", "label": "Bear Researcher", "index": 3},
    {"name": "debate", "label": "Debate", "index": 4},
    {"name": "jury_spawn", "label": "Jury Spawn", "index": 5},
    {"name": "jury_aggregate", "label": "Jury Aggregate", "index": 6},
    {"name": "risk_check", "label": "Risk Check", "index": 7},
    {"name": "pre_trade_validation", "label": "Pre-Trade Validation", "index": 8},
    {"name": "decision", "label": "Decision", "index": 9},
]


def _extract_node_data(node_name: str, state: TradingState) -> dict:
    """Extract the relevant data slice for a completed node."""
    if node_name == "quant_scoring":
        return {
            "quant_scores": state.quant_scores,
            "quant_composite": state.quant_composite,
            "quant_std_dev": state.quant_std_dev,
            "high_disagreement_flag": state.high_disagreement_flag,
        }
    elif node_name == "wasden_watch":
        return {
            "wasden_verdict": state.wasden_verdict,
            "wasden_confidence": state.wasden_confidence,
            "wasden_reasoning": state.wasden_reasoning,
            "wasden_mode": state.wasden_mode,
            "wasden_vetoed": state.wasden_vetoed,
        }
    elif node_name == "bull_researcher":
        return {"bull_case": state.bull_case[:200] + "..." if len(state.bull_case) > 200 else state.bull_case}
    elif node_name == "bear_researcher":
        return {"bear_case": state.bear_case[:200] + "..." if len(state.bear_case) > 200 else state.bear_case}
    elif node_name == "debate":
        return {
            "debate_outcome": state.debate_outcome,
            "debate_rounds": state.debate_rounds,
            "debate_agreed": state.debate_agreed,
        }
    elif node_name == "jury_spawn":
        return {"jury_spawned": state.jury_spawned, "jury_vote_count": len(state.jury_votes)}
    elif node_name == "jury_aggregate":
        return {
            "jury_result": state.jury_result,
            "jury_escalated": state.jury_escalated,
        }
    elif node_name == "risk_check":
        return {"risk_passed": state.risk_passed, "checks_failed": state.risk_check.get("checks_failed", [])}
    elif node_name == "pre_trade_validation":
        return {"pre_trade_passed": state.pre_trade_passed, "checks_failed": state.pre_trade_validation.get("checks_failed", [])}
    elif node_name == "decision":
        return {
            "final_action": state.final_action,
            "final_reason": state.final_reason,
            "recommended_position_size": state.recommended_position_size,
            "human_approval_required": state.human_approval_required,
        }
    return {}


class StreamingDecisionPipeline(DecisionPipeline):
    """Decision pipeline that yields SSE events as each node executes.

    Inherits all _node_* methods from DecisionPipeline. The run_stream()
    async generator wraps the synchronous node calls and yields event dicts
    between each step.
    """

    def __init__(self, use_mock: bool = True, random_seed: int = 42, mock_delay: float = 0.5):
        super().__init__(use_mock=use_mock, random_seed=random_seed)
        self._mock_delay = mock_delay if use_mock else 0.0

    async def run_stream(
        self,
        ticker: str,
        price: float,
        fundamentals: dict | None = None,
    ):
        """Async generator that yields SSE event dicts as each node runs."""
        state = TradingState(
            pipeline_run_id=str(uuid.uuid4()),
            ticker=ticker.upper(),
            price=price,
            fundamentals=fundamentals or {},
        )

        yield {
            "type": "pipeline_start",
            "pipeline_run_id": state.pipeline_run_id,
            "ticker": state.ticker,
            "total_nodes": len(PIPELINE_NODES),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            # Node 1: Quant scoring
            async for event in self._stream_node("quant_scoring", 0, state, self._node_quant_scoring):
                if isinstance(event, TradingState):
                    state = event
                else:
                    yield event

            # Node 2: Wasden Watch
            async for event in self._stream_node("wasden_watch", 1, state, self._node_wasden_watch):
                if isinstance(event, TradingState):
                    state = event
                else:
                    yield event

            # Short-circuit: Wasden VETO
            if state.wasden_vetoed:
                logger.info(f"[{state.ticker}] Wasden VETO — skipping nodes 2-8")
                for skip_node in PIPELINE_NODES[2:9]:
                    yield {
                        "type": "node_skipped",
                        "node": skip_node["name"],
                        "node_index": skip_node["index"],
                        "reason": "Wasden VETO — short-circuited to decision",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    if self._mock_delay > 0:
                        await asyncio.sleep(self._mock_delay * 0.2)

                async for event in self._stream_node("decision", 9, state, self._node_decision):
                    if isinstance(event, TradingState):
                        state = event
                    else:
                        yield event
            else:
                # Nodes 3-4: Bull and bear research
                async for event in self._stream_node("bull_researcher", 2, state, self._node_bull_researcher):
                    if isinstance(event, TradingState):
                        state = event
                    else:
                        yield event

                async for event in self._stream_node("bear_researcher", 3, state, self._node_bear_researcher):
                    if isinstance(event, TradingState):
                        state = event
                    else:
                        yield event

                # Node 5: Debate
                async for event in self._stream_node("debate", 4, state, self._node_debate):
                    if isinstance(event, TradingState):
                        state = event
                    else:
                        yield event

                # Conditional: Agreement → skip jury
                if state.debate_agreed:
                    for skip_node in PIPELINE_NODES[5:7]:
                        yield {
                            "type": "node_skipped",
                            "node": skip_node["name"],
                            "node_index": skip_node["index"],
                            "reason": "Debate agreement — jury not needed",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                        if self._mock_delay > 0:
                            await asyncio.sleep(self._mock_delay * 0.2)
                else:
                    # Nodes 6-7: Jury
                    async for event in self._stream_node("jury_spawn", 5, state, self._node_jury_spawn):
                        if isinstance(event, TradingState):
                            state = event
                        else:
                            yield event

                    async for event in self._stream_node("jury_aggregate", 6, state, self._node_jury_aggregate):
                        if isinstance(event, TradingState):
                            state = event
                        else:
                            yield event

                # Node 8: Risk check
                async for event in self._stream_node("risk_check", 7, state, self._node_risk_check):
                    if isinstance(event, TradingState):
                        state = event
                    else:
                        yield event

                # Node 9: Pre-trade validation
                async for event in self._stream_node("pre_trade_validation", 8, state, self._node_pre_trade_validation):
                    if isinstance(event, TradingState):
                        state = event
                    else:
                        yield event

                # Node 10: Decision
                async for event in self._stream_node("decision", 9, state, self._node_decision):
                    if isinstance(event, TradingState):
                        state = event
                    else:
                        yield event

            # Pipeline complete
            journal_entry = self._state_to_journal_entry(state)
            yield {
                "type": "pipeline_complete",
                "result": journal_entry,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"[{state.ticker}] Pipeline error: {e}")
            yield {
                "type": "pipeline_error",
                "error": str(e),
                "node": None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    async def _stream_node(self, node_name: str, node_index: int, state: TradingState, node_fn):
        """Async generator: yields node_start event, runs node, yields node_complete event, then yields updated state."""
        yield {
            "type": "node_start",
            "node": node_name,
            "node_index": node_index,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if self._mock_delay > 0:
            await asyncio.sleep(self._mock_delay)

        start_time = time.monotonic()
        state = node_fn(state)
        duration_ms = round((time.monotonic() - start_time) * 1000, 1)

        yield {
            "type": "node_complete",
            "node": node_name,
            "node_index": node_index,
            "duration_ms": duration_ms,
            "data": _extract_node_data(node_name, state),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Yield the updated state as the final item
        yield state
