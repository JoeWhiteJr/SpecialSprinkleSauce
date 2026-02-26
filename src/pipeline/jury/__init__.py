"""10-agent jury system — parallel voting with escalation on ties."""

from .jury_spawn import JurySpawner
from .jury_aggregate import JuryAggregator

__all__ = ["JurySpawner", "JuryAggregator"]
