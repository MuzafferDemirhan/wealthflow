"""CI diagnostic: verify all API routes are mounted before running tests."""
from app.main import app

routes = [getattr(r, "path", str(r)) for r in app.routes]
print("Total routes:", len(routes))
for r in sorted(routes):
    print(" ", r)

api_routes = [r for r in routes if "/api/v1" in r]
print("API v1 routes:", len(api_routes))
assert len(api_routes) > 0, "NO API ROUTES MOUNTED — import error somewhere"
print("OK — routes look good")
