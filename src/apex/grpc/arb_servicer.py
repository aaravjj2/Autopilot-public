"""gRPC servicer stubs wiring Redis L2 + arb scan (Week 1 Day 2)."""

from __future__ import annotations

import logging
import time
from typing import Callable

LOGGER = logging.getLogger(__name__)


def register_arb_grpc(server, list_opportunities_fn: Callable[[], list[dict]]) -> bool:
    """Register gRPC services if generated stubs exist."""
    try:
        from apex.grpc.generated import arb_pb2, arb_pb2_grpc
    except ImportError:
        LOGGER.warning("gRPC stubs missing; run scripts/generate_grpc.sh")
        return False

    from apex.cache.orderbook_l2 import ingest_orderbook

    class BrainServicer(arb_pb2_grpc.ArbBrainServiceServicer):
        def ScanOpportunities(self, request, context):
            limit = request.limit or 200
            rows = list_opportunities_fn()[:limit]
            msgs = [
                arb_pb2.ArbOpportunityMsg(
                    id=str(r.get("id", "")),
                    kalshi_ticker=str(r.get("kalshi_ticker", "")),
                    poly_market_id=str(r.get("poly_market_id", "")),
                    question=str(r.get("question", "")),
                    net_edge=float(r.get("net_edge") or 0),
                    gross_spread=float(r.get("gross_spread") or 0),
                    vwap_edge=float(r.get("vwap_edge") or 0),
                    kelly_fraction=float(r.get("kelly_fraction") or 0),
                    ai_confidence_score=float(r.get("ai_confidence_score") or 0),
                    category=str(r.get("category", "")),
                )
                for r in rows
            ]
            return arb_pb2.ArbScanResponse(
                opportunities=msgs, scanned_at_unix=int(time.time())
            )

        def RouteSignal(self, request, context):
            return arb_pb2.SignalRouteResponse(approved=True, reason="paper_mode")

    class IngestServicer(arb_pb2_grpc.OrderbookIngestServiceServicer):
        def PushOrderbook(self, request, context):
            book = {
                "yes": [[leg.price, leg.qty] for leg in request.yes_bids],
                "no": [[leg.price, leg.qty] for leg in request.no_bids],
            }
            ingest_orderbook(request.venue, request.ticker, book)
            return arb_pb2.OrderbookPushAck(
                ok=True, cache_key=f"orderbook:{request.venue}:{request.ticker}"
            )

    arb_pb2_grpc.add_ArbBrainServiceServicer_to_server(BrainServicer(), server)
    arb_pb2_grpc.add_OrderbookIngestServiceServicer_to_server(IngestServicer(), server)
    return True
