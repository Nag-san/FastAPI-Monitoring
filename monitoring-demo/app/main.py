from fastapi import FastAPI, Request, HTTPException
import time
import sys
import json
import random
import logging
from opentelemetry.trace import Status, StatusCode
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
import prometheus_client
from prometheus_client import Counter, Histogram
from prometheus_fastapi_instrumentator import Instrumentator
import uvicorn
from typing import Dict, Any, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Setup OpenTelemetry with proper resource
resource = Resource.create({
    "service.name": "fastapi-monitoring-demo",
    "service.version": "1.0.0",
    "environment": "development"
})

# Create tracer provider and set it
tracer_provider = TracerProvider(resource=resource)
trace.set_tracer_provider(tracer_provider)
tracer = trace.get_tracer(__name__)

# Setup OTLP exporter for traces
otlp_exporter = OTLPSpanExporter(
    endpoint="otel-collector:4317",  # Docker service name
    insecure=True  # Use TLS for production
)

# Add span processor to tracer provider
span_processor = BatchSpanProcessor(otlp_exporter)
tracer_provider.add_span_processor(span_processor)  # Fixed: use tracer_provider instance

# Setup metrics
REQUEST_COUNT = Counter('request_count', 'Total request count', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('request_latency_seconds', 'Request latency', ['method', 'endpoint'])
ERROR_COUNT = Counter('error_count', 'Total error count', ['method', 'endpoint', 'error_type'])

app = FastAPI(title="Monitoring Demo API")

# Instrument the app with OpenTelemetry
FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)

# Instrument the app with Prometheus
Instrumentator().instrument(app).expose(app)

def write_to_log_file(message: str) -> None:
    """Write logs to a file for Promtail to scrape"""
    try:
        with open('/var/log/app/app.log', 'a') as f:
            f.write(message + '\n')
    except Exception as e:
        print(f"Failed to write to log file: {e}")

class LokiFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            'time': int(record.created * 1e9),  # nanoseconds
            'level': record.levelname,
            'message': record.getMessage(),
            'logger': record.name,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Handle extra attributes safely
        extra_data = {}
        for key, value in record.__dict__.items():
            if key not in ['args', 'asctime', 'created', 'exc_info', 'exc_text', 
                          'filename', 'funcName', 'levelname', 'levelno', 'lineno',
                          'module', 'msecs', 'message', 'msg', 'name', 'pathname',
                          'process', 'processName', 'relativeCreated', 'stack_info',
                          'thread', 'threadName']:
                extra_data[key] = value
        
        if extra_data:
            log_data.update(extra_data)
            
        json_log = json.dumps(log_data)
        write_to_log_file(json_log)
        return json_log

# Create console handler with Loki formatter
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(LokiFormatter())
logger.addHandler(handler)

# Remove any existing handlers to avoid duplicate logs
logger.handlers = [handler]

def log_with_extra(message: str, extra_data: Optional[Dict[str, Any]] = None) -> None:
    """Helper function to log with extra data safely"""
    if extra_data:
        # Create a copy to avoid modifying the original dict
        log_extra = extra_data.copy()
        logger.info(message, extra=log_extra)
    else:
        logger.info(message)

@app.middleware("http")
async def monitor_requests(request: Request, call_next):
    start_time = time.time()
    
    with tracer.start_as_current_span(f"{request.method} {request.url.path}") as span:
        span.set_attribute("http.method", request.method)
        span.set_attribute("http.url", str(request.url))
        if request.client:
            span.set_attribute("http.client_ip", request.client.host)
        
        try:
            response = await call_next(request)
            processing_time = time.time() - start_time
            
            # Record metrics
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=request.url.path,
                status=response.status_code
            ).inc()
            
            REQUEST_LATENCY.labels(
                method=request.method,
                endpoint=request.url.path
            ).observe(processing_time)
            
            # Set span attributes
            span.set_attribute("http.status_code", response.status_code)
            span.set_attribute("http.response_time", processing_time)
            
            # Log the request safely
            log_extra = {
                'method': request.method,
                'endpoint': request.url.path,
                'status_code': response.status_code,
                'latency_seconds': round(processing_time, 3),
                'user_agent': request.headers.get('user-agent', ''),
                'trace_id': format(span.get_span_context().trace_id, '032x'),
                'span_id': format(span.get_span_context().span_id, '016x')
            }
            if request.client:
                log_extra['ip'] = request.client.host
            
            log_with_extra("Request processed", log_extra)
            
            return response
            
        except HTTPException as he:
            processing_time = time.time() - start_time
            ERROR_COUNT.labels(
                method=request.method,
                endpoint=request.url.path,
                error_type="http_error"
            ).inc()
            
            span.set_attribute("http.status_code", he.status_code)
            span.record_exception(he)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(he.detail)))
            
            logger.warning(f"HTTP Error: {he.detail}")
            raise
            
        except Exception as e:
            processing_time = time.time() - start_time
            ERROR_COUNT.labels(
                method=request.method,
                endpoint=request.url.path,
                error_type="server_error"
            ).inc()
            
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            
            logger.error(f"Server Error: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/")
async def root():
    # Start a new span for this endpoint
    with tracer.start_as_current_span("root_endpoint") as span:
        # Simulate some processing time
        processing_time = random.uniform(0.1, 0.5)
        time.sleep(processing_time)
        
        # Occasionally simulate errors (20% chance)
        if random.random() < 0.2:
            ERROR_COUNT.labels(
                method="GET",
                endpoint="/",
                error_type="simulated_error"
            ).inc()
            span.record_exception(ValueError("Simulated error"))
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Simulated error"))
            raise HTTPException(status_code=500, detail="Simulated server error")
        
        span.set_attribute("processing_time", processing_time)
        return {"message": "Hello World!", "processing_time": processing_time}

@app.get("/health")
async def health():
    with tracer.start_as_current_span("health_check"):
        # Simulate occasional health check failures (10% chance)
        if random.random() < 0.1:
            ERROR_COUNT.labels(
                method="GET",
                endpoint="/health",
                error_type="health_check_failed"
            ).inc()
            raise HTTPException(status_code=503, detail="Service temporarily unavailable")
        
        return {"status": "healthy", "timestamp": time.time()}

@app.get("/api/data")
async def get_data():
    with tracer.start_as_current_span("get_data_endpoint") as span:
        # Simulate data processing
        processing_time = random.uniform(0.2, 1.0)
        time.sleep(processing_time)
        
        # Simulate occasional data fetch errors (15% chance)
        if random.random() < 0.15:
            ERROR_COUNT.labels(
                method="GET",
                endpoint="/api/data",
                error_type="data_fetch_error"
            ).inc()
            span.record_exception(ValueError("Data fetch error"))
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Data not available"))
            raise HTTPException(status_code=404, detail="Data not available")
        
        data = {
            "items": [
                {"id": 1, "name": "Item 1"},
                {"id": 2, "name": "Item 2"},
                {"id": 3, "name": "Item 3"}
            ],
            "processing_time": processing_time,
            "timestamp": time.time()
        }
        
        span.set_attribute("data.items_count", len(data["items"]))
        span.set_attribute("processing_time", processing_time)
        
        return data
    
@app.get("/api/error-test")
async def error_test(type: Optional[str] = None):
    """Endpoint to test different error scenarios"""
    with tracer.start_as_current_span("error_test_endpoint") as span:
        error_type = type or random.choice(
            ["value_error", "key_error", "division_error"]
        )

        if error_type == "value_error":
            ERROR_COUNT.labels("GET", "/api/error-test", "value_error").inc()
            exc = ValueError("This is a simulated value error")
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, "Value error"))
            raise HTTPException(status_code=500, detail=str(exc))

        elif error_type == "key_error":
            ERROR_COUNT.labels("GET", "/api/error-test", "key_error").inc()
            exc = KeyError("This is a simulated key error")
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, "Key error"))
            raise HTTPException(status_code=500, detail=str(exc))

        else:  # division_error
            ERROR_COUNT.labels("GET", "/api/error-test", "division_error").inc()
            try:
                _ = 1 / 0
            except ZeroDivisionError as exc:
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, "Division error"))
                raise HTTPException(status_code=500, detail=str(exc))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)