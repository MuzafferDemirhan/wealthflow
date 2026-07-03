"""
Smoke tests - verify the app can be imported and basic config loads.
Real endpoint tests will be added in Sprint 1.
"""


def test_app_imports():
    from app.main import app
    assert app is not None


def test_app_title():
    from app.main import app
    assert app.title == "WealthFlow API"


def test_health_route_exists():
    from app.main import app
    routes = [r.path for r in app.routes]
    assert "/health" in routes


def test_settings_load():
    from app.core.config import settings
    assert settings.APP_NAME == "WealthFlow"
    assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 30
