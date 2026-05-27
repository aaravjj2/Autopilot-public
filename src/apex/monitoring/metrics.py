"""APEX Prometheus Metrics Exporter"""
from __future__ import annotations

import time
import logging
from collections import defaultdict
from typing import Any

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Collect and expose Prometheus-style metrics."""
    
    def __init__(self):
        self._counters: dict[str, float] = defaultdict(float)
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, list[float]] = defaultdict(list)
        self._start_time = time.time()
    
    def increment(self, name: str, value: float = 1.0, labels: dict[str, str] | None = None):
        """Increment a counter."""
        key = self._make_key(name, labels)
        self._counters[key] += value
    
    def set_gauge(self, name: str, value: float, labels: dict[str, str] | None = None):
        """Set a gauge value."""
        key = self._make_key(name, labels)
        self._gauges[key] = value
    
    def observe(self, name: str, value: float, labels: dict[str, str] | None = None):
        """Record an observation (histogram)."""
        key = self._make_key(name, labels)
        self._histograms[key].append(value)
    
    def _make_key(self, name: str, labels: dict[str, str] | None = None) -> str:
        if not labels:
            return name
        label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"
    
    def render_prometheus(self) -> str:
        """Render metrics in Prometheus exposition format."""
        lines = []
        
        # Counters
        for key, value in self._counters.items():
            lines.append(f"# TYPE {key.split('{')[0]} counter")
            lines.append(f"{key} {value}")
        
        # Gauges
        for key, value in self._gauges.items():
            lines.append(f"# TYPE {key.split('{')[0]} gauge")
            lines.append(f"{key} {value}")
        
        # Histograms
        for key, values in self._histograms.items():
            base_name = key.split('{')[0]
            lines.append(f"# TYPE {base_name} histogram")
            if values:
                lines.append(f"{base_name}_sum {sum(values)}")
                lines.append(f"{base_name}_count {len(values)}")
                # Simple bucket
                lines.append(f'{base_name}_bucket{{le="+Inf"}} {len(values)}')
        
        # Uptime
        uptime = time.time() - self._start_time
        lines.append("# TYPE apex_uptime_seconds gauge")
        lines.append(f"apex_uptime_seconds {uptime}")
        
        return "\n".join(lines) + "\n"


# Singleton
_metrics: MetricsCollector | None = None

def get_metrics() -> MetricsCollector:
    global _metrics
    if _metrics is None:
        _metrics = MetricsCollector()
    return _metrics
