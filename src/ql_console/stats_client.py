"""Live stats/events subscriber for Quake Live (ZeroMQ SUB socket).

Protocol (matches minqlx's _zmq.py):
  * socket type: SUB
  * PLAIN auth: username ``stats``, password = ``zmq_stats_password``, zap_domain ``stats``
  * SUBSCRIBE to everything ("")
  * no `register` step — the server publishes events; we passively receive them
  * each frame is a JSON object, typically ``{"TYPE": ..., "DATA": {...}}``

Runs on its own background thread; events are handed back through a callback.
"""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Callable

import zmq
from zmq.utils.monitor import recv_monitor_message

from .rcon_client import (
    ERR_AUTH_FAILED,
    ERR_TIMEOUT,
    HANDSHAKE_TIMEOUT_S,
    STATUS_CONNECTED,
    STATUS_CONNECTING,
    STATUS_DISCONNECTED,
    STATUS_ERROR,
)

_POLL_TIMEOUT_MS = 200


class StatsClient:
    """Background subscriber to a server's live event stream."""

    def __init__(
        self,
        endpoint: str,
        password: str,
        on_event: Callable[[dict], None],
        on_status: Callable[[str, str], None],
    ) -> None:
        self._endpoint = endpoint
        self._password = password
        self._on_event = on_event
        self._on_status = on_status

        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, name=f"stats-{self._endpoint}", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=2.0)
        self._thread = None

    # -- background thread ------------------------------------------------

    def _run(self) -> None:
        self._on_status(STATUS_CONNECTING, self._endpoint)
        ctx = zmq.Context.instance()
        socket = ctx.socket(zmq.SUB)
        socket.setsockopt(zmq.LINGER, 0)
        if self._password:
            socket.plain_username = b"stats"
            socket.plain_password = self._password.encode()
            socket.zap_domain = b"stats"
        socket.setsockopt_string(zmq.SUBSCRIBE, "")

        # SUB sockets connect asynchronously and have no `register` handshake,
        # so we watch the monitor socket to learn when the connection is
        # actually established instead of optimistically announcing it.
        monitor = socket.get_monitor_socket()
        connected_ever = False
        deadline = time.monotonic() + HANDSHAKE_TIMEOUT_S
        auth_fail_event = getattr(zmq, "EVENT_HANDSHAKE_FAILED_AUTH", None)
        try:
            socket.connect(self._endpoint)
            while not self._stop.is_set():
                try:
                    ev = recv_monitor_message(monitor, zmq.NOBLOCK)
                    event = ev["event"]
                    if event == zmq.EVENT_CONNECTED:
                        if not connected_ever:
                            connected_ever = True
                            self._on_status(STATUS_CONNECTED, self._endpoint)
                    elif auth_fail_event is not None and event == auth_fail_event:
                        self._on_status(STATUS_ERROR, ERR_AUTH_FAILED)
                        break
                except zmq.error.Again:
                    pass

                # Never completed a handshake within the grace period.
                if not connected_ever and time.monotonic() > deadline:
                    self._on_status(STATUS_ERROR, ERR_TIMEOUT)
                    break

                if socket.poll(_POLL_TIMEOUT_MS) == 0:
                    continue
                while True:
                    try:
                        raw = socket.recv(zmq.NOBLOCK)
                    except zmq.error.Again:
                        break
                    self._dispatch(raw)
        except Exception as exc:
            self._on_status(STATUS_ERROR, str(exc))
        finally:
            try:
                socket.disable_monitor()
                monitor.close(0)
            except Exception:
                pass
            socket.close(0)
            if connected_ever:
                self._on_status(STATUS_DISCONNECTED, self._endpoint)

    def _dispatch(self, raw: bytes) -> None:
        try:
            event = json.loads(raw.decode(errors="ignore"))
        except (json.JSONDecodeError, ValueError):
            return
        if isinstance(event, dict):
            self._on_event(event)
