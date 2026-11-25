import pytest
from fastapi.routing import APIRoute
from limits import parse_many

from src.api.dependencies import get_session_user_id, require_auth
from src.core.limiter import clear_limit, hit_limit, limit_reached, limiter
from src.main import app


@pytest.fixture(autouse=True)
def fresh_counters():
    limiter.reset()


def uses(dependant, call) -> bool:
    return any(item.call is call or uses(item, call) for item in dependant.dependencies)


# The routes of every router of the app: app.routes only has one entry per router
def api_routes() -> list[APIRoute]:
    included = [route for route in app.routes if hasattr(route, "original_router")]
    routers = [route.original_router for route in included]  # pyright: ignore[reportAttributeAccessIssue]
    return [route for router in routers for route in router.routes if isinstance(route, APIRoute)]


def counts_per_user(route: APIRoute) -> bool:
    limits = limiter._route_limits[f"{route.endpoint.__module__}.{route.endpoint.__name__}"]
    return bool(limits) and all(limit.key_func is get_session_user_id for limit in limits)


def test_hit_limit_counts_each_identifier_apart():
    assert hit_limit("2/minute", "test", "a") and hit_limit("2/minute", "test", "a")
    assert not hit_limit("2/minute", "test", "a")
    assert hit_limit("2/minute", "test", "b")


def test_hit_limit_stops_at_the_first_limit_reached():
    assert hit_limit("1/minute;5/hour", "test", "a")
    assert not hit_limit("1/minute;5/hour", "test", "a")


# Like the decorator: a storage that fails doesn't block the request
def test_hit_limit_lets_through_when_the_storage_fails(monkeypatch, caplog):
    def broken(*args, **kwargs):
        raise ConnectionError("redis down")

    monkeypatch.setattr(limiter.limiter, "hit", broken)

    assert hit_limit("1/minute", "test", "a") and hit_limit("1/minute", "test", "a")
    assert "Rate limit storage failed" in caplog.text


# A limit written wrong is a bug: it can't pass for a storage that failed and turn the limit off
@pytest.mark.parametrize("function", [hit_limit, limit_reached, clear_limit])
def test_a_limit_written_wrong_is_an_error(function):
    with pytest.raises(ValueError):
        function("5/minuet", "test", "a")


def test_limit_reached_doesnt_count_a_use():
    assert not limit_reached("1/minute", "test", "a") and not limit_reached("1/minute", "test", "a")

    hit_limit("1/minute", "test", "a")

    assert limit_reached("1/minute", "test", "a") and not limit_reached("1/minute", "test", "b")


def test_limit_reached_looks_at_every_limit():
    hit_limit("1/minute;5/hour", "test", "a")

    assert limit_reached("5/hour;1/minute", "test", "a")


# Like hit_limit: a storage that fails doesn't block the request
def test_limit_reached_answers_no_when_the_storage_fails(monkeypatch, caplog):
    def broken(*args, **kwargs):
        raise ConnectionError("redis down")

    monkeypatch.setattr(limiter.limiter, "test", broken)

    assert not limit_reached("1/minute", "test", "a")
    assert "Rate limit storage failed" in caplog.text


def test_clear_limit_forgets_every_limit_of_that_identifier_and_only_those():
    hit_limit("1/minute;1/hour", "test", "a")
    hit_limit("1/minute;1/hour", "test", "b")

    clear_limit("1/minute;1/hour", "test", "a")

    assert not limit_reached("1/minute;1/hour", "test", "a")
    assert limit_reached("1/minute;1/hour", "test", "b")


# Like hit_limit: a storage that fails doesn't stop the request
def test_clear_limit_goes_on_when_the_storage_fails(monkeypatch, caplog):
    def broken(*args, **kwargs):
        raise ConnectionError("redis down")

    monkeypatch.setattr(limiter.limiter, "clear", broken)

    clear_limit("1/minute", "test", "a")

    assert "Rate limit storage failed" in caplog.text


# A day can't be waited for in a test: the limits of each route are read from its decorator
@pytest.mark.parametrize("route, limits", [
    ("auth_router.login", "60/minute;2000/day"),
    ("auth_router.logout", "60/minute;2000/day"),
    ("auth_router.forgot_password", "30/minute;300/day"),
    ("auth_router.reset_password", "30/minute;300/day"),
    ("user_router.me", "120/minute;5000/day"),
])
def test_each_route_has_its_limits(route, limits):
    found = [str(limit.limit) for limit in limiter._route_limits[f"src.api.routers.{route}"]]

    assert found == [str(item) for item in parse_many(limits)]


def test_no_route_goes_without_a_limit():
    routes = [route.endpoint for route in api_routes()]

    assert routes and [
        route.__name__ for route in routes if f"{route.__module__}.{route.__name__}" not in limiter._route_limits
    ] == []


# Per IP, one client flooding a route with a session would leave a whole school without it
def test_every_route_with_a_session_counts_per_user():
    routes = [route for route in api_routes() if uses(route.dependant, require_auth)]

    assert {route.path for route in routes} == {"/auth/logout", "/user/me"}
    assert all(counts_per_user(route) for route in routes)


# Without a session the key has no user: a 500, and slowapi would take it for a storage that failed
def test_only_a_route_with_a_session_counts_per_user():
    routes = [route for route in api_routes() if counts_per_user(route)]

    assert routes and all(uses(route.dependant, require_auth) for route in routes)
