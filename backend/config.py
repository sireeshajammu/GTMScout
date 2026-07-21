"""Central configuration for the GTMScout agent backend."""

# --- LLM Configuration ---
# Kept on OpenAI gpt-4o-mini 
MODEL = "gpt-4o-mini"
TEMPERATURE = 0.4          # a touch lower for more grounded, consistent analysis
MAX_TOKENS = 1200

# --- Retry Configuration ---
MAX_RETRIES = 3
RETRY_DELAY = 2            # base for exponential backoff (seconds)

# --- Agent Configuration ---
AGENT_TIMEOUT = 30        # seconds

# --- Cost tracking ---
TRACK_TOKENS = True
# gpt-4o-mini pricing (USD per 1M tokens). Update if OpenAI changes rates.
COST_PER_1M_INPUT = 0.15
COST_PER_1M_OUTPUT = 0.60


def usd_cost(tokens_in: int, tokens_out: int) -> float:
    """Estimate USD cost for a given token usage on the configured model."""
    return round(
        (tokens_in / 1_000_000) * COST_PER_1M_INPUT
        + (tokens_out / 1_000_000) * COST_PER_1M_OUTPUT,
        6,
    )
