"""ASGI timing with fixed labels; stream contents and request data are never logged."""

from time import perf_counter

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from k_loto.application.runtime_monitoring import runtime_monitoring


class RequestMetricsMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        path = scope.get("path", "")
        if (
            scope["type"] != "http"
            or not path.startswith("/api/v1/miniapp/")
            or path.endswith(("/stream", "/telemetry"))
        ):
            await self.app(scope, receive, send)
            return
        status, start = 500, perf_counter()

        async def observed(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, observed)
        finally:
            duration = (perf_counter() - start) * 1000
            runtime_monitoring.record("miniapp", duration, status)
            label = (
                "purchase"
                if path.endswith("/purchases")
                else "dashboard"
                if path.endswith("/dashboard")
                else "account"
                if path.endswith("/account")
                else None
            )
            if label:
                runtime_monitoring.record(label, duration, status)
