"""Load canonical agent prompts from anthropic/financial-services for LLM context."""

from __future__ import annotations

import re
from pathlib import Path

from apex.core.logging import get_logger

LOGGER = get_logger(__name__)


def _strip_frontmatter(md: str) -> str:
    if md.lstrip().startswith("---"):
        parts = md.split("---", 2)
        if len(parts) >= 3:
            return parts[2].lstrip()
    return md


def load_financial_services_augmentation(repo_path: str, max_chars: int = 8000) -> str:
    """
    Concatenate trimmed Market Researcher + Earnings Reviewer agent prompts when
    ANTHROPIC_FINANCIAL_SERVICES_REPO_PATH points at a checkout of that repo.
    """
    if not repo_path:
        return ""
    root = Path(repo_path).expanduser().resolve()
    if not root.is_dir():
        LOGGER.warning("financial-services repo not found at %s", root)
        return ""
    chunks: list[str] = []
    for rel in (
        "plugins/agent-plugins/market-researcher/agents/market-researcher.md",
        "plugins/agent-plugins/earnings-reviewer/agents/earnings-reviewer.md",
    ):
        p = root / rel
        if p.is_file():
            text = _strip_frontmatter(p.read_text(encoding="utf-8", errors="replace"))
            text = re.sub(r"\s+", " ", text).strip()
            chunks.append(f"## {rel}\n{text}")
    if not chunks:
        return ""
    joined = "\n\n".join(chunks)
    if len(joined) > max_chars:
        joined = joined[: max_chars - 20] + "\n...[truncated]"
    return (
        "\n\nThe following institutional research standards apply "
        "(adapt tool references to data you actually have):\n\n" + joined
    )
