"""RCON client for Quake Live (ZeroMQ DEALER socket).

Protocol (matches the stock zmq_rcon.py / minqlx clients):
  * socket type: DEALER
  * PLAIN auth: username ``rcon``, password = ``zmq_rcon_password``, zap_domain ``rcon``
  * a random IDENTITY is set
  * after the monitor reports EVENT_CONNECTED we must send ``register`` once
  * commands are sent as raw bytes; the server replies with text frames

All socket I/O happens on a dedicated background thread. Results are delivered
to the caller through plain callbacks; the GUI layer is responsible for
marshalling them onto the wx main thread (via wx.CallAfter).
"""

from __future__ import annotations

import threading
import uuid
from collections.abc import Callable
from queue import Empty, Queue

import zmq
from zmq.utils.monitor import recv_monitor_message

# Status values reported through the on_status callback.
STATUS_CONNECTING = "connecting"
STATUS_CONNECTED = "connected"
STATUS_DISCONNECTED = "disconnected"
STATUS_ERROR = "error"

_POLL_TIMEOUT_MS = 100


class RconClient:
    """Background RCON connection to a single server."""

    def __init__(
        self,
        endpoint: str,
        password: str,
        on_message: Callable[[str], None],
        on_status: Callable[[str, str], None],
    ) -> None:
        self._endpoint = endpoint
        self._password = password
        self._on_message = on_message
        self._on_status = on_status

        self._outgoing: Queue[str] = Queue()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        # The server emits console output as many small frames (one per
        # Com_Printf call); a line isn't complete until a "\n" arrives. We
        # accumulate frames here and split on newlines.
        self._rx_buffer = ""

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, name=f"rcon-{self._endpoint}", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=2.0)
        self._thread = None

    def send(self, command: str) -> None:
        """Queue a command to be sent to the server."""
        self._outgoing.put(command)

    # -- background thread ------------------------------------------------

    def _run(self) -> None:
        self._rx_buffer = ""
        self._on_status(STATUS_CONNECTING, self._endpoint)
        ctx = zmq.Context.instance()
        socket = ctx.socket(zmq.DEALER)
        # Printable identity so the server's echo ("RCON command from <id>")
        # stays readable instead of showing raw bytes.
        socket.setsockopt(zmq.IDENTITY, b"qlconsole-" + uuid.uuid4().hex.encode())
        socket.setsockopt(zmq.LINGER, 0)
        if self._password:
            socket.plain_username = b"rcon"
            socket.plain_password = self._password.encode()
            socket.zap_domain = b"rcon"

        monitor = socket.get_monitor_socket()
        registered = False
        try:
            socket.connect(self._endpoint)
            while not self._stop.is_set():
                # Watch the monitor socket for the initial handshake so we know
                # when to (re-)send the mandatory `register` frame.
                try:
                    ev = recv_monitor_message(monitor, zmq.NOBLOCK)
                    if ev["event"] == zmq.EVENT_CONNECTED:
                        socket.send(b"register")
                        registered = True
                        self._on_status(STATUS_CONNECTED, self._endpoint)
                    elif ev["event"] == zmq.EVENT_DISCONNECTED:
                        registered = False
                        self._on_status(STATUS_DISCONNECTED, self._endpoint)
                except zmq.error.Again:
                    pass

                self._drain_outgoing(socket, registered)
                self._drain_incoming(socket)

                socket.poll(_POLL_TIMEOUT_MS)
        except Exception as exc:  # surface any unexpected socket failure
            self._on_status(STATUS_ERROR, str(exc))
        finally:
            try:
                socket.disable_monitor()
                monitor.close(0)
            except Exception:
                pass
            socket.close(0)
            self._on_status(STATUS_DISCONNECTED, self._endpoint)

    def _drain_outgoing(self, socket: zmq.Socket, registered: bool) -> None:
        if not registered:
            return
        while True:
            try:
                command = self._outgoing.get_nowait()
            except Empty:
                break
            socket.send(command.encode())

    def _drain_incoming(self, socket: zmq.Socket) -> None:
        while True:
            try:
                msg = socket.recv(zmq.NOBLOCK)
            except zmq.error.Again:
                break
            self._rx_buffer += msg.decode(errors="replace")
            # Emit each complete (newline-terminated) line; keep the remainder.
            while "\n" in self._rx_buffer:
                line, _, self._rx_buffer = self._rx_buffer.partition("\n")
                self._on_message(line)
            # Safety valve: don't let an unterminated line grow without bound.
            if len(self._rx_buffer) > 8192:
                self._on_message(self._rx_buffer)
                self._rx_buffer = ""
