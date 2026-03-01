#!/usr/bin/env python3
"""Wyoming protocol server for OpenClaw integration."""

import argparse
import asyncio
import json
import logging
import signal
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from wyoming.asr import Transcript
from wyoming.event import Event, async_read_event, async_write_event
from wyoming.info import Attribution, Describe, Info, HandleProgram, HandleModel
from wyoming.handle import Handled, NotHandled

_LOGGER = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 90


class OpenClawHandler:
    """Handle Wyoming events for OpenClaw."""

    def __init__(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        gateway_url: str,
        gateway_token: str,
        agent_id: str,
        session_user: str,
        timeout: int,
    ) -> None:
        self.reader = reader
        self.writer = writer
        self.gateway_url = gateway_url
        self.gateway_token = gateway_token
        self.agent_id = agent_id
        self.session_user = session_user
        self.timeout = timeout

    async def handle_event(self, event: Event) -> bool:
        """Handle incoming Wyoming event."""
        _LOGGER.debug("Received event type: %s", event.type)

        if Describe.is_type(event.type):
            info = Info(
                handle=[
                    HandleProgram(
                        name="openclaw",
                        description="OpenClaw AI Assistant",
                        attribution=Attribution(
                            name="OpenClaw",
                            url="https://openclaw.ai",
                        ),
                        installed=True,
                        version="1.0.0",
                        models=[
                            HandleModel(
                                name="openclaw",
                                description="OpenClaw multilingual assistant",
                                attribution=Attribution(
                                    name="OpenClaw",
                                    url="https://openclaw.ai",
                                ),
                                installed=True,
                                version="1.0.0",
                                languages=[
                                    "en",
                                    "ru",
                                    "de",
                                    "fr",
                                    "es",
                                    "it",
                                    "pt",
                                    "nl",
                                    "pl",
                                    "uk",
                                ],
                            )
                        ],
                    )
                ]
            )
            await async_write_event(info.event(), self.writer)
            _LOGGER.debug("Sent info response")
            return True

        if Transcript.is_type(event.type):
            transcript = Transcript.from_event(event)
            _LOGGER.info("Received transcript: %s", transcript.text)

            try:
                response_text = await self._call_openclaw(transcript.text)
                _LOGGER.info("OpenClaw response: %s", response_text)
                handled = Handled(text=response_text)
                await async_write_event(handled.event(), self.writer)
            except asyncio.TimeoutError:
                _LOGGER.error(
                    "OpenClaw timed out after %ds for: %s",
                    self.timeout,
                    transcript.text,
                )
                not_handled = NotHandled(text="Превышено время ожидания ответа.")
                await async_write_event(not_handled.event(), self.writer)
            except asyncio.CancelledError:
                _LOGGER.warning("Request cancelled for: %s", transcript.text)
                raise
            except Exception as e:
                _LOGGER.error("Error calling OpenClaw: %s", e)
                not_handled = NotHandled(text=f"Ошибка: {e}")
                await async_write_event(not_handled.event(), self.writer)

            return True

        _LOGGER.warning("Unexpected event type: %s", event.type)
        return True

    async def _call_openclaw(self, text: str) -> str:
        """Call OpenClaw Gateway HTTP API and return response."""
        url = f"{self.gateway_url}/v1/chat/completions"
        body = json.dumps(
            {
                "model": f"openclaw:{self.agent_id}",
                "messages": [{"role": "user", "content": text}],
                "user": self.session_user,
            }
        ).encode()

        req = Request(url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", f"Bearer {self.gateway_token}")

        loop = asyncio.get_running_loop()
        try:
            response = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: urlopen(req, timeout=self.timeout),
                ),
                timeout=self.timeout,
            )
            data = json.loads(response.read().decode())
        except asyncio.TimeoutError:
            _LOGGER.warning("Gateway HTTP timed out after %ds", self.timeout)
            raise
        except HTTPError as e:
            body_text = e.read().decode() if e.fp else ""
            raise RuntimeError(f"Gateway HTTP {e.code}: {body_text}") from e
        except URLError as e:
            raise RuntimeError(f"Gateway connection failed: {e.reason}") from e

        choices = data.get("choices", [])
        if choices:
            content = choices[0].get("message", {}).get("content", "")
            if content:
                return content
        return "No response from OpenClaw."

    async def run(self) -> None:
        """Run the handler loop."""
        try:
            while True:
                event = await async_read_event(self.reader)
                if event is None:
                    break
                if not await self.handle_event(event):
                    break
        except asyncio.CancelledError:
            _LOGGER.debug("Handler cancelled")
        finally:
            self.writer.close()


async def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Wyoming server for OpenClaw")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=10400, help="Port to listen on")
    parser.add_argument("--agent", default="main", help="OpenClaw agent id")
    parser.add_argument(
        "--session-user",
        default="voice-assistant",
        help="OpenAI user field for session routing",
    )
    parser.add_argument(
        "--gateway-url",
        default="http://127.0.0.1:18789",
        help="OpenClaw Gateway HTTP URL",
    )
    parser.add_argument("--gateway-token", help="OpenClaw Gateway auth token")
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help="Timeout in seconds for OpenClaw calls",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    gateway_token = args.gateway_token or ""
    if not gateway_token:
        _LOGGER.warning("No --gateway-token provided, requests may fail")

    _LOGGER.info(
        "Starting Wyoming-OpenClaw server on %s:%d (gateway=%s, agent=%s, timeout=%ds)",
        args.host,
        args.port,
        args.gateway_url,
        args.agent,
        args.timeout,
    )

    tasks: set[asyncio.Task] = set()

    async def handle_client(
        reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        peer = writer.get_extra_info("peername")
        _LOGGER.debug("Client connected: %s", peer)
        handler = OpenClawHandler(
            reader,
            writer,
            gateway_url=args.gateway_url,
            gateway_token=gateway_token,
            agent_id=args.agent,
            session_user=args.session_user,
            timeout=args.timeout,
        )
        task = asyncio.current_task()
        if task is not None:
            tasks.add(task)
        try:
            await handler.run()
        finally:
            _LOGGER.debug("Client disconnected: %s", peer)
            if task is not None:
                tasks.discard(task)

    server = await asyncio.start_server(handle_client, args.host, args.port)

    loop = asyncio.get_running_loop()
    stop = loop.create_future()

    def _signal_handler() -> None:
        if not stop.done():
            stop.set_result(None)

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _signal_handler)

    _LOGGER.info("Server ready, waiting for connections")

    async with server:
        await stop

    _LOGGER.info("Shutting down, cancelling %d active handlers", len(tasks))
    for t in tasks:
        t.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


if __name__ == "__main__":
    asyncio.run(main())
