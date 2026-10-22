"""Request-scoped Ollama transport for the website, not benchmark workers.

No retries, no global prompt logging. The caller may attach an observer while
testing synthetic requests. The 8s embedding / 16s chat caps are unchanged;
the remaining API deadline is an additional total limit.
"""
import asyncio
from concurrent.futures import CancelledError as FutureCancelled, TimeoutError as FutureTimeout
from contextlib import asynccontextmanager
from contextvars import ContextVar
import json
import threading
import time

import httpx

from app.rag.embedding import OllamaClient, OllamaError


_request = ContextVar("website_ollama_request", default=None)


class RequestScope:
    def __init__(self, seconds, observer):
        self.started = time.perf_counter()
        self.deadline = self.started + seconds
        self.loop = asyncio.get_running_loop()
        self.observer = observer
        self.cancelled = threading.Event()
        self.pending = set()
        self.tasks = set()
        self.lock = threading.Lock()
        self.client = None

    def remaining(self):
        return max(0.0, self.deadline - time.perf_counter())

    def emit(self, stage, **values):
        if self.observer:
            self.observer({"stage": stage, "at_ms": (time.perf_counter() - self.started) * 1000, **values})

    def cancel(self):
        self.cancelled.set()
        with self.lock:
            for future in tuple(self.pending):
                future.cancel()


@asynccontextmanager
async def website_request(seconds, observer=None):
    scope = RequestScope(seconds, observer)
    token = _request.set(scope)
    try:
        yield scope
    finally:
        scope.cancel()
        # A concurrent Future is marked cancelled before the coroutine has
        # closed its response socket. Join the actual I/O tasks as well.
        tasks = tuple(scope.tasks)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        if scope.client is not None:
            await scope.client.aclose()
        scope.emit("request_closed", active_io_tasks=len(scope.tasks))
        _request.reset(token)


def emit(stage, **values):
    scope = _request.get()
    if scope:
        scope.emit(stage, **values)


class WebsiteOllamaClient(OllamaClient):
    def _post(self, path, payload, timeout=120):
        scope = _request.get()
        if scope is None:
            # Standalone callers keep the existing synchronous contract.
            return super()._post(path, payload, timeout)
        if scope.cancelled.is_set() or scope.remaining() <= 0:
            raise OllamaError("Website request already cancelled")
        future = asyncio.run_coroutine_threadsafe(self._post_async(scope, path, payload, timeout), scope.loop)
        with scope.lock:
            if scope.cancelled.is_set():
                future.cancel()
            else:
                scope.pending.add(future)
        try:
            return future.result(timeout=scope.remaining() + 0.05)
        except (FutureCancelled, FutureTimeout) as exc:
            future.cancel()
            raise OllamaError("Website request cancelled or timed out") from exc
        finally:
            with scope.lock:
                scope.pending.discard(future)

    async def _post_async(self, scope, path, payload, timeout):
        task = asyncio.current_task()
        scope.tasks.add(task)
        try:
            return await self._send(scope, path, payload, timeout)
        finally:
            scope.tasks.discard(task)

    async def _send(self, scope, path, payload, timeout):
        if scope.cancelled.is_set():
            raise OllamaError("Website request cancelled before dispatch")
        budget = min(float(timeout), scope.remaining())
        if budget <= 0:
            raise OllamaError("Website deadline exhausted")
        if scope.client is None:
            # Async TCP uses happy-eyeballs for localhost IPv6/IPv4 and reuses
            # the same connection for embedding and chat within this request.
            # HTTP loopback needs no TLS context/certificate loading. HTTPS
            # deployments still verify certificates; redirects are disabled.
            scope.client = httpx.AsyncClient(base_url=self.base_url + "/", trust_env=False,
                                            verify=self.base_url.lower().startswith("https://"),
                                            timeout=httpx.Timeout(budget, connect=min(3, budget)))
        budget = min(float(timeout), scope.remaining())
        if scope.cancelled.is_set() or budget <= 0:
            raise OllamaError("Website deadline exhausted before dispatch")
        body = dict(payload)
        if path == "/api/chat":
            body["stream"] = True
        scope.emit("ollama_start", path=path, model=body.get("model"), options=body.get("options"),
                   timeout_seconds=budget, payload=body)
        started = time.perf_counter()
        try:
            async with asyncio.timeout(budget):
                async with scope.client.stream("POST", path.lstrip("/"), json=body,
                                               timeout=httpx.Timeout(budget, connect=min(3, budget))) as response:
                    response.raise_for_status()
                    if path == "/api/chat":
                        chunks, final, first_token = [], {}, None
                        async for line in response.aiter_lines():
                            if not line:
                                continue
                            item = json.loads(line)
                            if item.get("error"):
                                raise OllamaError("Ollama generation error")
                            content = item.get("message", {}).get("content", "")
                            if content and first_token is None:
                                first_token = (time.perf_counter() - started) * 1000
                            chunks.append(content)
                            final = item
                        if not final.get("done"):
                            raise OllamaError("Ollama stream ended before completion")
                        result = {**final, "message": {"role": "assistant", "content": "".join(chunks)}}
                        scope.emit("ollama_done", path=path, ms=(time.perf_counter() - started) * 1000,
                                   first_token_ms=first_token, response=result)
                        return result
                    result = json.loads(await response.aread())
                    scope.emit("ollama_done", path=path, ms=(time.perf_counter() - started) * 1000,
                               embedding_dimensions=len(result.get("embedding", [])))
                    return result
        except asyncio.CancelledError:
            scope.emit("ollama_cancelled", path=path, ms=(time.perf_counter() - started) * 1000)
            raise
        except (httpx.HTTPError, TimeoutError, ValueError) as exc:
            scope.emit("ollama_error", path=path, ms=(time.perf_counter() - started) * 1000,
                       error=type(exc).__name__)
            raise OllamaError("Website Ollama request failed") from exc
