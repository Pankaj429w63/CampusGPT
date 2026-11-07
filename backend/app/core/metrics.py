import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

# Prometheus Metrics Definitions
HTTP_REQUESTS_TOTAL = Counter(
    "campusgpt_http_requests_total",
    "Total HTTP requests handled by CampusGPT backend",
    ["method", "endpoint", "status"]
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "campusgpt_http_request_duration_seconds",
    "HTTP request latency breakdown in seconds",
    ["endpoint"],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 15.0, 30.0]
)

STAGE_LATENCY_SECONDS = Histogram(
    "campusgpt_stage_latency_seconds",
    "Latency breakdown by internal pipeline stage",
    ["stage"],
    buckets=[0.005, 0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 15.0]
)

GUARDRAIL_VIOLATIONS_TOTAL = Counter(
    "campusgpt_guardrail_violations_total",
    "Total guardrail rule violations detected",
    ["violation_type"]
)

TOOL_CALLS_TOTAL = Counter(
    "campusgpt_tool_calls_total",
    "Total specialized tool executions invoked by query planner",
    ["tool_name", "status"]
)

class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.perf_counter()
        endpoint = request.url.path
        
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            status_code = 500
            raise
        finally:
            duration = time.perf_counter() - start_time
            # Avoid metric cardinality explosion for high-cardinality paths if any
            normalized_endpoint = endpoint if endpoint in [
                "/", "/health", "/readiness", "/ready", "/ask", "/ingest",
                "/metrics", "/evaluate", "/evaluation/summary", "/agents/status"
            ] else "other"
            
            HTTP_REQUESTS_TOTAL.labels(
                method=request.method,
                endpoint=normalized_endpoint,
                status=str(status_code)
            ).inc()
            
            HTTP_REQUEST_DURATION_SECONDS.labels(
                endpoint=normalized_endpoint
            ).observe(duration)
            
        return response

def get_metrics_content():
    return generate_latest(), CONTENT_TYPE_LATEST

