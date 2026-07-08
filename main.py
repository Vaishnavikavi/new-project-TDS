import time
import uuid

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

ALLOWED_ORIGIN = "https://dash-3dg4dj.example.com"
EMAIL = "24ds2000025@ds.study.iitm.ac.in"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN],
    allow_credentials=False,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_headers(request, call_next):
    start = time.perf_counter()

    response = await call_next(request)

    elapsed = time.perf_counter() - start

    response.headers["X-Request-ID"] = str(uuid.uuid4())
    response.headers["X-Process-Time"] = f"{elapsed:.6f}"

    return response


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
