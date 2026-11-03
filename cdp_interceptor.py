import asyncio
import base64
import json
import sys
import urllib.request
import websockets
from typing import Dict, Any

# Pillar 8: UTF-8 Console Safety Guard
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from config import CDP_PORT
from rules import RuleEngine
from proxy_server import logger

# Maximum file size to buffer in memory for packet interception (50 MB)
MAX_BUFFER_CONTENT_LENGTH = 50 * 1024 * 1024
STREAMING_MEDIA_THRESHOLD = 10 * 1024 * 1024

class CDPInterceptor:
    def __init__(self, cdp_port: int = CDP_PORT):
        self.cdp_port = cdp_port
        self.ws = None
        self.msg_id = 0
        self.rule_engine = RuleEngine()
        self.running = False

    async def get_browser_ws_url(self) -> str:
        url = f"http://127.0.0.1:{self.cdp_port}/json/version"
        for _ in range(30):
            try:
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req, timeout=2) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    return data.get("webSocketDebuggerUrl")
            except Exception:
                await asyncio.sleep(0.5)
        raise RuntimeError("Failed to connect to Edge CDP within timeout.")

    async def send(self, method: str, params: Dict[str, Any] = None, session_id: str = None) -> int:
        self.msg_id += 1
        msg = {"id": self.msg_id, "method": method}
        if params:
            msg["params"] = params
        if session_id:
            msg["sessionId"] = session_id
        await self.ws.send(json.dumps(msg))
        return self.msg_id

    async def start(self):
        self.running = True
        try:
            ws_url = await self.get_browser_ws_url()
            print(f"[CDP Interceptor] Connected to Edge: {ws_url}")
        except Exception as e:
            print(f"[CDP Interceptor] Connection failed: {e}")
            return

        async with websockets.connect(ws_url, max_size=100 * 1024 * 1024) as ws:
            self.ws = ws

            # Auto-attach to all pages/tabs/workers with flatten=True
            await self.send("Target.setAutoAttach", {
                "autoAttach": True,
                "waitForDebuggerOnStart": False,
                "flatten": True
            })

            # Also enable Target discovery
            await self.send("Target.setDiscoverTargets", {"discover": True})

            async for message in ws:
                if not self.running:
                    break
                try:
                    data = json.loads(message)
                    await self.handle_message(data)
                except Exception:
                    pass

    async def handle_message(self, data: Dict[str, Any]):
        method = data.get("method")
        params = data.get("params", {})
        session_id = data.get("sessionId")

        if method == "Target.attachedToTarget":
            target_type = params.get("targetInfo", {}).get("type")
            if target_type in ("page", "iframe"):
                await self.send("Fetch.enable", {
                    "patterns": [
                        {"urlPattern": "*", "requestStage": "Request"},
                        {"urlPattern": "*", "requestStage": "Response"}
                    ]
                }, session_id=session_id)

        elif method == "Fetch.requestPaused":
            await self.handle_request_paused(params, session_id)

    async def handle_request_paused(self, params: Dict[str, Any], session_id: str):
        req_id = params.get("requestId")
        req = params.get("request", {})
        url = req.get("url", "")
        method = req.get("method", "GET")
        response_status = params.get("responseStatusCode")

        # Skip local dashboard or devtools requests
        if "127.0.0.1" in url or "localhost" in url or url.startswith("devtools://") or url.startswith("edge://"):
            if response_status:
                await self.send("Fetch.continueResponse", {"requestId": req_id}, session_id=session_id)
            else:
                await self.send("Fetch.continueRequest", {"requestId": req_id}, session_id=session_id)
            return

        rules = self.rule_engine.match_request_rules(url)

        # STAGE 1: Request Stage
        if not response_status:
            for r in rules:
                action = r.get("action")
                if action == "block":
                    logger.log(method, url, status=403, modified=True)
                    await self.send("Fetch.failRequest", {
                        "requestId": req_id,
                        "errorReason": "BlockedByClient"
                    }, session_id=session_id)
                    return

                if action == "mock_response":
                    body_str = r.get("mock_body", '{"mocked": true}')
                    body_b64 = base64.b64encode(body_str.encode("utf-8")).decode("ascii")
                    headers = [
                        {"name": "Content-Type", "value": r.get("mock_content_type", "application/json; charset=utf-8")},
                        {"name": "Access-Control-Allow-Origin", "value": "*"}
                    ]
                    logger.log(method, url, status=r.get("mock_status", 200), modified=True)
                    await self.send("Fetch.fulfillRequest", {
                        "requestId": req_id,
                        "responseCode": r.get("mock_status", 200),
                        "responseHeaders": headers,
                        "body": body_b64
                    }, session_id=session_id)
                    return

                if action == "modify_request":
                    add_h = r.get("add_request_headers", {})
                    if add_h:
                        cur_headers = req.get("headers", {})
                        for k, v in add_h.items():
                            cur_headers[k] = v
                        headers_list = [{"name": k, "value": str(v)} for k, v in cur_headers.items()]
                        logger.log(method, url, status=200, modified=True)
                        await self.send("Fetch.continueRequest", {
                            "requestId": req_id,
                            "headers": headers_list
                        }, session_id=session_id)
                        return

            await self.send("Fetch.continueRequest", {"requestId": req_id}, session_id=session_id)
            return

        # STAGE 2: Response Stage
        raw_headers = params.get("responseHeaders", [])
        headers_dict = {h["name"].lower(): h["value"] for h in raw_headers}

        # [Radar Item 1] Large File Streaming Memory Safety Guard
        content_len_str = headers_dict.get("content-length", "0")
        try:
            content_len = int(content_len_str)
        except ValueError:
            content_len = 0

        content_type = headers_dict.get("content-type", "").lower()
        is_large = content_len > MAX_BUFFER_CONTENT_LENGTH
        is_media_stream = any(t in content_type for t in ["application/octet-stream", "application/zip", "video/", "audio/"]) and content_len > STREAMING_MEDIA_THRESHOLD

        if is_large or is_media_stream:
            # Pass-through streaming immediately without buffering in RAM
            logger.log(method, url, status=response_status, modified=False)
            await self.send("Fetch.continueResponse", {"requestId": req_id}, session_id=session_id)
            return

        has_resp_mods = any(r.get("action") == "modify_response" for r in rules)
        if has_resp_mods:
            for r in rules:
                if r.get("action") == "modify_response":
                    for k, v in r.get("add_response_headers", {}).items():
                        headers_dict[k.lower()] = v
                    for rem in r.get("remove_response_headers", []):
                        headers_dict.pop(rem.lower(), None)

            new_headers = [{"name": k, "value": v} for k, v in headers_dict.items()]
            logger.log(method, url, status=response_status, modified=True)
            await self.send("Fetch.continueResponse", {
                "requestId": req_id,
                "responseCode": response_status,
                "responseHeaders": new_headers
            }, session_id=session_id)
            return

        logger.log(method, url, status=response_status)
        await self.send("Fetch.continueResponse", {"requestId": req_id}, session_id=session_id)
