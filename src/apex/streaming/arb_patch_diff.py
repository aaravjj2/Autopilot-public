"""RFC 6902 JSON Patch diff for arb opportunity snapshots (Week 1 Day 3)."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def _index_by_id(rows: list[dict[str, Any]]) -> dict[str, int]:
    return {str(r.get("id")): i for i, r in enumerate(rows) if r.get("id") is not None}


def diff_opportunities(
    previous: list[dict[str, Any]],
    current: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Produce JSON Patch ops for `/opportunities` document root.
    Paths use array indices matching sorted-by-net_edge order in `current`.
    """
    patches: list[dict[str, Any]] = []
    prev_by_id = {str(r["id"]): r for r in previous if r.get("id")}
    curr_by_id = {str(r["id"]): r for r in current if r.get("id")}
    curr_index = _index_by_id(current)

    for opp_id, row in curr_by_id.items():
        idx = curr_index[opp_id]
        if opp_id not in prev_by_id:
            patches.append({"op": "add", "path": "/opportunities/-", "value": row})
            continue
        old = prev_by_id[opp_id]
        for key, val in row.items():
            if old.get(key) != val:
                patches.append(
                    {"op": "replace", "path": f"/opportunities/{idx}/{key}", "value": val}
                )

    prev_index = _index_by_id(previous)
    remove_indices = sorted(
        (prev_index[opp_id] for opp_id in prev_by_id if opp_id not in curr_by_id),
        reverse=True,
    )
    for idx in remove_indices:
        patches.append({"op": "remove", "path": f"/opportunities/{idx}"})

    return patches


def apply_patch_document(
    document: dict[str, Any],
    patches: list[dict[str, Any]],
) -> dict[str, Any]:
    """Apply RFC 6902 patches (requires jsonpatch library)."""
    import jsonpatch

    doc = deepcopy(document)
    return jsonpatch.JsonPatch(patches).apply(doc)
