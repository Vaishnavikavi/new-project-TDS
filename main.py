import time
import uuid

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Header
from typing import Optional
import base64

from collections import deque
from prometheus_client import Counter, generate_latest
from fastapi.responses import Response
ALLOWED_ORIGIN = "https://dash-3dg4dj.example.com"
EMAIL = "24ds2000025@ds.study.iitm.ac.in"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.middleware("http")
async def add_headers(request, call_next):
    start = time.perf_counter()
    request_id = str(uuid.uuid4())

    http_requests_total.inc()

    response = await call_next(request)

    elapsed = time.perf_counter() - start

    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = f"{elapsed:.6f}"

    logs.append({
        "level": "INFO",
        "ts": time.time(),
        "path": str(request.url.path),
        "request_id": request_id,
    })

    return response

TOTAL_ORDERS = 45
RATE_LIMIT = 17
WINDOW = 10  # seconds

# For idempotency
idempotency_store = {}

# For rate limiting
client_requests = {}

# Order ID generator
next_order_id = 1
@app.get("/stats")
def stats(values: str = Query(...)):
    nums = [int(x.strip()) for x in values.split(",") if x.strip()]

    return {
        "email": EMAIL,
        "count": len(nums),
        "sum": sum(nums),
        "min": min(nums),
        "max": max(nums),
        "mean": sum(nums) / len(nums),
    }
PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA2okOHspNjgA+2rTLbeuY
cxiP/hG8C6Sb9iwg3yiLAA4HCnpITcbWCSelbvbYGuc3EbNy4xFyf5Cbj5DHJMID
EkryOgyd2giIIIBOUBj8S63uGcnRpOBh9NFatfNwheKuzsPuVNldu6A9cNteNpXc
WyJjG2axVfmq7i6SuKr1JoWYG7xTTAvKPujSl4OtsQfO3h5NepzdfXpr28oNnzfW
ed+zclR6BcmNNo/WVfJ4xyCLSf0BCOgdTgW6PdaChd1l9VDetJZVEgC5tkyvXsfI
SI6iyrYbKR0NEBSqq4XkadEjsCs4F1RncsS4LlgniT7GlkL9Mce3b0wGLs9/7ZIX
dQIDAQAB
-----END PUBLIC KEY-----"""

import jwt
from jwt import InvalidTokenError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

class TokenRequest(BaseModel):
    token: str

@app.post("/verify")
def verify(request: TokenRequest):
    try:
        payload = jwt.decode(
            request.token,
            PUBLIC_KEY,
            algorithms=["RS256"],
            issuer="https://idp.exam.local",
            audience="tds-1st4at3m.apps.exam.local",
        )

        return {
            "valid": True,
            "email": payload["email"],
            "sub": payload["sub"],
            "aud": payload["aud"],
        }

    except InvalidTokenError:
        return JSONResponse(
            status_code=401,
            content={"valid": False},
        )


import os
import yaml
from dotenv import dotenv_values
from fastapi import Request

DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}

def to_bool(value):
    return str(value).lower() in ("true", "1", "yes", "on")

def coerce(key, value):
    if key in ("port", "workers"):
        return int(value)
    if key == "debug":
        return to_bool(value)
    return str(value)

@app.get("/effective-config")
def effective_config(request: Request):
    config = DEFAULTS.copy()

    # YAML
    with open("config.development.yaml") as f:
        config.update(yaml.safe_load(f))

    # .env
    env_file = dotenv_values(".env")
    if "APP_PORT" in env_file:
        config["port"] = int(env_file["APP_PORT"])
    if "NUM_WORKERS" in env_file:
        config["workers"] = int(env_file["NUM_WORKERS"])
    if "APP_LOG_LEVEL" in env_file:
        config["log_level"] = env_file["APP_LOG_LEVEL"]

    # OS environment
    if os.getenv("APP_PORT"):
        config["port"] = int(os.getenv("APP_PORT"))
    if os.getenv("APP_WORKERS"):
        config["workers"] = int(os.getenv("APP_WORKERS"))
    if os.getenv("APP_DEBUG"):
        config["debug"] = to_bool(os.getenv("APP_DEBUG"))
    if os.getenv("APP_LOG_LEVEL"):
        config["log_level"] = os.getenv("APP_LOG_LEVEL")
    if os.getenv("APP_API_KEY"):
        config["api_key"] = os.getenv("APP_API_KEY")

    # CLI overrides
    overrides = request.query_params.getlist("set")

    for item in overrides:
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        config[key] = coerce(key, value)

    config["api_key"] = "****"

    return config




from fastapi import Header, HTTPException
from pydantic import BaseModel
from typing import List

class Event(BaseModel):
    user: str
    amount: float
    ts: int

class AnalyticsRequest(BaseModel):
    events: List[Event]

API_KEY = "ak_lhd3a560ypjj7jmp6gpax9ik"

@app.post("/analytics")
def analytics(
    request: AnalyticsRequest,
    x_api_key: str = Header(None)
):
    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized"
        )

    events = request.events

    revenue = 0.0
    totals = {}

    for event in events:
        if event.amount > 0:
            revenue += event.amount
            totals[event.user] = totals.get(event.user, 0) + event.amount

    top_user = max(totals, key=totals.get) if totals else ""

    return {
        "email": EMAIL,
        "total_events": len(events),
        "unique_users": len(set(e.user for e in events)),
        "revenue": revenue,
        "top_user": top_user,
    }

START_TIME = time.time()

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests"
)

logs = deque(maxlen=1000)

@app.get("/work")
def work(n: int = 1):
    # Do K units of work
    for _ in range(n):
        pass

    return {
        "email": EMAIL,
        "done": n
    }


@app.get("/metrics")
def metrics():
    return Response(
        generate_latest(),
        media_type="text/plain"
    )


@app.get("/healthz")
def healthz():
    return {
        "status": "ok",
        "uptime_s": time.time() - START_TIME
    }


@app.get("/logs/tail")
def logs_tail(limit: int = 10):
    return list(logs)[-limit:]


def encode_cursor(index: int):
    return base64.b64encode(str(index).encode()).decode()


def decode_cursor(cursor: Optional[str]):
    if not cursor:
        return 0
    return int(base64.b64decode(cursor.encode()).decode())

def check_rate_limit(client_id: str):
    now = time.time()

    if client_id not in client_requests:
        client_requests[client_id] = []

    requests = client_requests[client_id]

    # Keep only requests from last 10 seconds
    requests[:] = [t for t in requests if now - t < WINDOW]

    if len(requests) >= RATE_LIMIT:
        return False

    requests.append(now)
    return True


@app.post("/orders", status_code=201)
def create_order(
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    client_id: str = Header(..., alias="X-Client-Id")
):
    global next_order_id

    if not check_rate_limit(client_id):
        return Response(
            status_code=429,
            headers={"Retry-After": "10"}
        )

    if idempotency_key in idempotency_store:
        return idempotency_store[idempotency_key]

    order = {
        "id": next_order_id
    }

    next_order_id += 1

    idempotency_store[idempotency_key] = order

    return order

@app.get("/orders")
def list_orders(
    limit: int = 10,
    cursor: str = None,
    x_client_id: str = Header(..., alias="X-Client-Id")
):
    if not check_rate_limit(x_client_id):
        return Response(
            status_code=429,
            headers={"Retry-After": "10"}
        )

    start = decode_cursor(cursor)

    end = min(start + limit, TOTAL_ORDERS)

    items = []

    for i in range(start + 1, end + 1):
        items.append({
            "id": i
        })

    next_cursor = None

    if end < TOTAL_ORDERS:
        next_cursor = encode_cursor(end)

    return {
        "items": items,
        "next_cursor": next_cursor
    }


