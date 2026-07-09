FASTAPI_LOGIN_API_BLUEPRINT = {
    "product_type": "FASTAPI_SERVICE",
    "product_name": "FastAPI Login API",
    "artifacts": [
        "app/__init__.py",
        "app/main.py",
        "app/routers/__init__.py",
        "app/routers/auth.py",
        "app/schemas.py",
        "tests/test_health.py",
        "tests/test_login.py",
        "requirements.txt",
        "README.md",
        "openapi.json",
    ],
    "features": [
        "GET /health",
        "POST /login",
        "JWT authentication response",
        "OpenAPI documentation",
        "Pytest coverage",
    ],
}
