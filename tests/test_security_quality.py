from zabbix_mcp.server import call_tool
from zabbix_mcp.tools import handle_get_events
from zabbix_mcp.user_management import UserManagement


def test_password_validation_enforces_minimum_complexity() -> None:
    errors = UserManagement._validate_password("short", "admin")
    assert "Password must be at least 8 characters long" in errors
    assert "Password must contain at least one number" in errors
    assert "Password must contain at least one special character" in errors


def test_handle_get_events_rejects_out_of_range_limit() -> None:
    result = handle_get_events(client=None, args={"limit": 0})  # type: ignore[arg-type]
    assert "limit must be between 1 and 1000" in result


class _FakeHandler:
    def __call__(self, _client, _arguments):
        raise RuntimeError("sensitive details")


def test_call_tool_does_not_leak_internal_exception(monkeypatch) -> None:
    import zabbix_mcp.server as server_module

    server_module.client = object()  # type: ignore[assignment]
    monkeypatch.setattr(server_module, "get_tool_handler", lambda _name: _FakeHandler())

    response = __import__("asyncio").run(call_tool("x", {}))
    assert response[0].text == "Error executing tool"
