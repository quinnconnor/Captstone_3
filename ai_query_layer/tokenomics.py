"""
Tracks token usage and cost for every Bedrock call made by the AI query
layer (classification/routing, SQL generation, contextual response
generation), and produces a cost summary after a test run.

Pricing below is Claude Sonnet-class list pricing per 1M tokens as of this
assignment's timeframe (Anthropic direct-API list price, used here as a
reasonable Bedrock-equivalent estimate). Update PRICE_PER_MILLION_INPUT /
PRICE_PER_MILLION_OUTPUT if your Bedrock invoice shows a different rate.
"""
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict

PRICE_PER_MILLION_INPUT_TOKENS = 3.00
PRICE_PER_MILLION_OUTPUT_TOKENS = 15.00

_CALL_LOG = []


@dataclass
class BedrockCallRecord:
    call_type: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def cost_usd(self) -> float:
        input_cost = (self.input_tokens / 1_000_000) * PRICE_PER_MILLION_INPUT_TOKENS
        output_cost = (self.output_tokens / 1_000_000) * PRICE_PER_MILLION_OUTPUT_TOKENS
        return round(input_cost + output_cost, 6)


def log_bedrock_call(call_type: str, input_tokens: int, output_tokens: int,
                      latency_ms: float = 0.0) -> BedrockCallRecord:
    record = BedrockCallRecord(
        call_type=call_type, input_tokens=input_tokens,
        output_tokens=output_tokens, latency_ms=latency_ms,
    )
    _CALL_LOG.append(record)
    return record


def get_call_log() -> list:
    return list(_CALL_LOG)


def reset_call_log():
    _CALL_LOG.clear()


def cost_summary() -> dict:
    """Aggregates the call log into a per-call-type and total cost summary."""
    summary_by_type = {}
    for record in _CALL_LOG:
        bucket = summary_by_type.setdefault(record.call_type, {
            "calls": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0,
        })
        bucket["calls"] += 1
        bucket["input_tokens"] += record.input_tokens
        bucket["output_tokens"] += record.output_tokens
        bucket["cost_usd"] += record.cost_usd

    for bucket in summary_by_type.values():
        bucket["cost_usd"] = round(bucket["cost_usd"], 6)

    total_calls = len(_CALL_LOG)
    total_input = sum(r.input_tokens for r in _CALL_LOG)
    total_output = sum(r.output_tokens for r in _CALL_LOG)
    total_cost = round(sum(r.cost_usd for r in _CALL_LOG), 6)

    return {
        "by_call_type": summary_by_type,
        "totals": {
            "total_calls": total_calls,
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_cost_usd": total_cost,
            "avg_cost_per_call_usd": round(total_cost / total_calls, 6) if total_calls else 0.0,
        },
        "pricing_assumptions": {
            "price_per_million_input_tokens_usd": PRICE_PER_MILLION_INPUT_TOKENS,
            "price_per_million_output_tokens_usd": PRICE_PER_MILLION_OUTPUT_TOKENS,
        },
    }


def print_cost_summary():
    summary = cost_summary()
    print("\n=== Tokenomics Cost Summary ===")
    for call_type, stats in summary["by_call_type"].items():
        print(f"  [{call_type}] calls={stats['calls']} "
              f"input_tokens={stats['input_tokens']} output_tokens={stats['output_tokens']} "
              f"cost=${stats['cost_usd']:.6f}")
    totals = summary["totals"]
    print(f"  TOTAL: calls={totals['total_calls']} "
          f"input_tokens={totals['total_input_tokens']} "
          f"output_tokens={totals['total_output_tokens']} "
          f"cost=${totals['total_cost_usd']:.6f} "
          f"(avg ${totals['avg_cost_per_call_usd']:.6f}/call)")
