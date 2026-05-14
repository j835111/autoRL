from auto_rl.config import ResearchConfig

from .base import AutoResearcher, ResearchDecision
from .heuristic import HeuristicAutoResearcher
from .llm import LLMAutoResearcher


def build_researcher(config: ResearchConfig) -> AutoResearcher | None:
    if not config.enabled:
        return None

    mode = config.mode.lower()
    if mode == "heuristic":
        return HeuristicAutoResearcher(config)
    if mode == "llm":
        return LLMAutoResearcher(config)
    if mode in {"off", "disabled"}:
        return None
    raise ValueError(f"Unsupported researcher mode: {config.mode}")

__all__ = [
    "AutoResearcher",
    "HeuristicAutoResearcher",
    "LLMAutoResearcher",
    "ResearchDecision",
    "build_researcher",
]
