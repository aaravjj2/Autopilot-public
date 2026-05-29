"""FinanceBrain: the autopilot's reasoning layer.

Uses Groq, local Ollama, or OpenRouter when available; otherwise falls back to
deterministic heuristics grounded in the finance knowledge base so paper-trading
and the morning chain never stall waiting on a cloud LLM.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from apex.brain import finance_knowledge as kb

LOGGER = logging.getLogger(__name__)

_MAX_OUTPUT_TOKENS = 700


@dataclass
class BrainVerdict:
    """Structured opinion the autopilot can act on or log."""

    action: str  # "EXECUTE" | "SKIP" | "REVIEW"
    confidence: float  # 0..1
    rationale: str
    risks: list[str] = field(default_factory=list)
    source: str = "heuristic"  # "llm:<label>" or "heuristic"

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "confidence": round(float(self.confidence), 3),
            "rationale": self.rationale,
            "risks": list(self.risks),
            "source": self.source,
        }


@dataclass
class _RouteSlot:
    label: str
    model: str
    client: Any | None = None
    native_gemini_key: str = ""
    dead: bool = False


class FinanceBrain:
    """LLM-backed finance reasoner with offline heuristic fallback."""

    def __init__(self, settings: Any | None = None) -> None:
        if settings is None:
            from apex.core.config import get_settings

            settings = get_settings()
        self._settings = settings
        self._routes: list[_RouteSlot] = []
        self._route_label: str = "heuristic"
        self._model: str = ""
        self._resolve_routes()

    # -- route resolution -----------------------------------------------------
    def _resolve_routes(self) -> None:
        self._routes = []
        self._route_label = "heuristic"
        self._model = ""
        try:
            from apex.core.gemini_native import uses_query_key_auth
            from apex.core.llm_routing import openai_client_from_route, resolve_llm_routes

            for route in resolve_llm_routes(self._settings):
                slot = _RouteSlot(
                    label=route.label,
                    model=route.deep_think_model or route.model,
                )
                if route.label == "gemini" and uses_query_key_auth(route.api_key):
                    slot.native_gemini_key = route.api_key
                else:
                    slot.client = openai_client_from_route(route)
                    if slot.client is None and not slot.native_gemini_key:
                        continue
                self._routes.append(slot)
        except Exception as exc:  # pragma: no cover - defensive
            LOGGER.warning("FinanceBrain route resolution failed: %s", exc)

        if self._routes:
            self._route_label = self._routes[0].label
            self._model = self._routes[0].model

    @property
    def is_live(self) -> bool:
        """True when at least one LLM backend is configured and not disabled."""
        return any(not slot.dead and (slot.client is not None or slot.native_gemini_key) for slot in self._routes)

    @property
    def operational(self) -> bool:
        """True when the brain can answer (LLM and/or heuristic/scripts)."""
        return True

    @property
    def route_label(self) -> str:
        active = self._active_slot()
        return active.label if active is not None else "heuristic"

    def _active_slot(self) -> _RouteSlot | None:
        for slot in self._routes:
            if not slot.dead and (slot.client is not None or slot.native_gemini_key):
                return slot
        return None

    def status(self, *, probe: bool = False) -> dict[str, Any]:
        active = self._active_slot()
        out: dict[str, Any] = {
            "operational": True,
            "live": self.is_live,
            "mode": active.label if active else "heuristic",
            "provider": active.label if active else "heuristic",
            "model": active.model if active else "",
            "routes": [s.label for s in self._routes if not s.dead],
            "knowledge_version": kb.KNOWLEDGE_VERSION,
            "knowledge_cards": len(kb.all_cards()),
        }
        if active is not None and active.native_gemini_key:
            out["auth_mode"] = "query_key"
        elif active is not None and active.client is not None:
            out["auth_mode"] = "bearer"
        if not self.is_live:
            out["fallback"] = "heuristic"
        if probe and self.is_live:
            text, probe_label, err = self._probe_llm()
            out["probe_provider"] = probe_label
            if text and "GEMINI_OK" in text.upper():
                out["authenticated"] = True
                out["probe"] = "ok"
            elif text:
                out["authenticated"] = True
                out["probe"] = "degraded"
                out["probe_detail"] = text[:120]
            elif err:
                out.update(_classify_probe_error(err))
            else:
                out["authenticated"] = False
                out["probe"] = "failed"
        active = self._active_slot()
        out["live"] = self.is_live
        out["mode"] = active.label if active else "heuristic"
        out["provider"] = out["mode"]
        out["model"] = active.model if active else ""
        if not self.is_live:
            out["fallback"] = "heuristic"
        return out

    # -- public ops -----------------------------------------------------------
    def ask(self, question: str, *, context: str | None = None) -> str:
        """Free-form analyst answer grounded in the strategy knowledge base."""
        system = kb.build_system_prompt(question)
        user = question if not context else f"Context:\n{context}\n\nQuestion: {question}"
        text, label = self._chat(system, user)
        if text is not None:
            return text
        # Fallback: surface the most relevant doctrine deterministically.
        cards = kb.retrieve(question, limit=3)
        bullets = "\n".join(f"- {c.title}: {c.content}" for c in cards)
        return (
            "[brain offline — knowledge-based answer]\n"
            f"{bullets}"
        )

    def analyze_opportunity(self, opp: Any) -> BrainVerdict:
        """Return a structured verdict for an arbitrage opportunity."""
        facts = _opp_facts(opp)
        system = kb.build_system_prompt(
            "prediction market arbitrage settlement liquidity sizing risk"
        )
        user = (
            "Evaluate this paper-trading arbitrage opportunity. Respond ONLY with "
            "minified JSON: {\"action\":\"EXECUTE|SKIP|REVIEW\",\"confidence\":0..1,"
            "\"rationale\":\"...\",\"risks\":[\"...\"]}.\n\n"
            f"OPPORTUNITY:\n{json.dumps(facts, default=str)}"
        )
        text, label = self._chat(system, user)
        verdict = _parse_verdict(text, label) if text else None
        if verdict is not None:
            return verdict
        return _heuristic_verdict(facts)

    # -- llm plumbing ---------------------------------------------------------
    def _probe_llm(self) -> tuple[str | None, str, str]:
        for slot in self._routes:
            if slot.dead:
                continue
            try:
                text = self._invoke_slot(
                    slot,
                    "You are a health probe.",
                    "Reply with exactly: GEMINI_OK",
                    max_tokens=20,
                    temperature=0.0,
                )
                if text:
                    self._route_label = slot.label
                    self._model = slot.model
                    return text, slot.label, ""
            except Exception as exc:
                err = str(exc)
                if _disable_slot(slot, exc):
                    continue
                return None, slot.label, err
        return None, "heuristic", ""

    def _chat(self, system: str, user: str) -> tuple[str | None, str]:
        if not self.is_live:
            return None, "heuristic"
        for slot in self._routes:
            if slot.dead:
                continue
            try:
                text = self._invoke_slot(
                    slot,
                    system,
                    user,
                    max_tokens=_MAX_OUTPUT_TOKENS,
                    temperature=0.2,
                )
                if text:
                    self._route_label = slot.label
                    self._model = slot.model
                    return text, slot.label
            except Exception as exc:
                LOGGER.warning(
                    "FinanceBrain LLM call failed (%s); trying next route: %s",
                    slot.label,
                    exc,
                )
                _disable_slot(slot, exc)
        return None, "heuristic"

    def _invoke_slot(
        self,
        slot: _RouteSlot,
        system: str,
        user: str,
        *,
        max_tokens: int,
        temperature: float,
    ) -> str | None:
        if slot.native_gemini_key:
            from apex.core.gemini_native import generate_content

            text = generate_content(
                slot.native_gemini_key,
                slot.model,
                system=system,
                user=user,
                max_output_tokens=max_tokens,
                temperature=temperature,
            )
            return text.strip() if text and text.strip() else None
        if slot.client is None:
            return None
        resp = slot.client.chat.completions.create(
            model=slot.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        choice = resp.choices[0]
        content = getattr(choice.message, "content", None)
        if isinstance(content, str) and content.strip():
            return content.strip()
        return None


def _disable_slot(slot: _RouteSlot, exc: BaseException) -> bool:
    from apex.core.llm_routing import llm_error_disables_route

    if llm_error_disables_route(exc):
        slot.dead = True
        slot.client = None
        slot.native_gemini_key = ""
        return True
    return False


def _classify_probe_error(msg: str) -> dict[str, Any]:
    lower = msg.lower()
    if "429" in msg or "resource_exhausted" in lower:
        return {
            "authenticated": True,
            "probe": "quota_exhausted",
            "probe_detail": msg[:200],
        }
    if "organization_restricted" in lower or "organization has been restricted" in lower:
        return {
            "authenticated": False,
            "probe": "provider_restricted",
            "probe_detail": msg[:200],
        }
    if any(token in lower for token in ("403", "401", "api_key", "permission_denied", "invalid api key")):
        return {
            "authenticated": False,
            "probe": "auth_failed",
            "probe_detail": msg[:200],
        }
    return {"authenticated": False, "probe": "failed", "probe_detail": msg[:200]}


# ---------------------------------------------------------------------------
# Helpers (module-level for testability)
# ---------------------------------------------------------------------------
def _gv(opp: Any, name: str, default: Any = None) -> Any:
    if isinstance(opp, dict):
        return opp.get(name, default)
    return getattr(opp, name, default)


def _opp_facts(opp: Any) -> dict[str, Any]:
    flags = _gv(opp, "settlement_flags", []) or []
    if isinstance(flags, str):
        # The SQLite store serializes flags as a JSON string.
        try:
            parsed = json.loads(flags)
            flags = parsed if isinstance(parsed, list) else []
        except (json.JSONDecodeError, TypeError):
            flags = [flags] if flags.strip() else []
    return {
        "id": _gv(opp, "id"),
        "question": _gv(opp, "question") or _gv(opp, "kalshi_title"),
        "net_edge": _as_float(_gv(opp, "net_edge")),
        "gross_spread": _as_float(_gv(opp, "gross_spread")),
        "settlement_match_score": _as_float(_gv(opp, "settlement_match_score")),
        "settlement_flags": list(flags),
        "volume_kalshi": _as_float(_gv(opp, "volume_kalshi")),
        "volume_poly": _as_float(_gv(opp, "volume_poly")),
        "kalshi_yes_ask": _as_float(_gv(opp, "kalshi_yes_ask")),
        "poly_no_ask": _as_float(_gv(opp, "poly_no_ask")),
    }


def _as_float(v: Any) -> float:
    try:
        return float(v) if v is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def _parse_verdict(text: str, label: str) -> BrainVerdict | None:
    raw = _extract_json(text)
    if raw is None:
        return None
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    action = str(data.get("action", "REVIEW")).upper().strip()
    if action not in {"EXECUTE", "SKIP", "REVIEW"}:
        action = "REVIEW"
    try:
        conf = float(data.get("confidence", 0.0))
    except (TypeError, ValueError):
        conf = 0.0
    conf = max(0.0, min(1.0, conf))
    risks_raw = data.get("risks", [])
    risks = [str(r) for r in risks_raw] if isinstance(risks_raw, list) else []
    return BrainVerdict(
        action=action,
        confidence=conf,
        rationale=str(data.get("rationale", "")).strip() or "(no rationale)",
        risks=risks,
        source=f"llm:{label}",
    )


def _extract_json(text: str) -> str | None:
    """Pull the first balanced JSON object out of an LLM response."""
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def _heuristic_verdict(facts: dict[str, Any]) -> BrainVerdict:
    """Deterministic, knowledge-consistent fallback verdict.

    Mirrors the doctrine in finance_knowledge: net edge after costs, settlement
    confidence, liquidity, and flag count drive the decision. Fails closed.
    """
    edge = facts["net_edge"]
    settle = facts["settlement_match_score"]
    flags = facts["settlement_flags"]
    min_vol = min(facts["volume_kalshi"], facts["volume_poly"])

    risks: list[str] = []
    if settle < 0.55:
        risks.append("low settlement-match score: title match may not be a true arb")
    if flags:
        risks.append(f"{len(flags)} settlement flag(s): {', '.join(map(str, flags[:3]))}")
    if min_vol < 2000:
        risks.append(f"thin liquidity on the smaller leg (~${min_vol:,.0f} 24h)")
    if edge <= 0:
        risks.append("non-positive net edge after costs")

    # Decision logic (fails closed toward SKIP/REVIEW).
    if edge <= 0 or settle < 0.55 or min_vol < 2000 or len(flags) > 2:
        action = "SKIP"
        confidence = 0.7
        rationale = (
            "Fails a hard quality gate (edge/settlement/liquidity/flags); "
            "skipping per risk-first doctrine."
        )
    elif edge >= 0.03 and settle >= 0.8 and min_vol >= 10000 and not flags:
        action = "EXECUTE"
        confidence = min(0.95, 0.5 + edge * 4 + (settle - 0.8))
        rationale = (
            f"Clean two-leg arb: net edge {edge:.1%}, settlement {settle:.2f}, "
            f"min-leg liquidity ~${min_vol:,.0f}, no flags."
        )
    else:
        action = "REVIEW"
        confidence = 0.5
        rationale = (
            "Marginal opportunity: positive but modest edge or borderline "
            "settlement/liquidity. Worth a human/secondary check."
        )
    return BrainVerdict(
        action=action,
        confidence=confidence,
        rationale=rationale,
        risks=risks,
        source="heuristic",
    )


# ---------------------------------------------------------------------------
# Process-wide singleton (cheap to reuse; re-resolves route on demand)
# ---------------------------------------------------------------------------
_BRAIN: FinanceBrain | None = None


def get_brain(settings: Any | None = None, *, refresh: bool = False) -> FinanceBrain:
    global _BRAIN
    if _BRAIN is None or refresh:
        _BRAIN = FinanceBrain(settings)
    return _BRAIN
