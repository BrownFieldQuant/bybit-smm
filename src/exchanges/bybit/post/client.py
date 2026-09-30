
import json
import time
import hashlib
import hmac
import aiohttp
import asyncio

from src.exchanges.bybit.endpoints import BaseEndpoints
from src.utils.misc import curr_dt


class BybitPrivatePostClient:


    def __init__(self, api_key: str, api_secret: str) -> None:
        self.base_endpoint = BaseEndpoints.MAINNET1
        self.api_key = api_key
        self.api_secret = api_secret
        self.recvWindow = "5000"
    
    
    def _sign(self, payload) -> dict:
        self.timestamp = str(int(time.time()*1000))
        param_str = "".join([self.timestamp, self.api_key, self.recvWindow, str(payload)])

        header = {
            "X-BAPI-TIMESTAMP": self.timestamp,
            "X-BAPI-API-KEY": self.api_key,
            "X-BAPI-RECV-WINDOW": self.recvWindow,
        }

        hash_signature = hmac.new(
            bytes(self.api_secret, "utf-8"), 
            param_str.encode("utf-8"), 
            hashlib.sha256
        )

        header["X-BAPI-SIGN"] = hash_signature.hexdigest()

        return header


    async def submit(self, session: aiohttp.ClientSession, endpoint: str, payload: dict):
    payload_str = json.dumps(payload, separators=(",", ":"))
    full_endpoint = self.base_endpoint + endpoint

    max_retries = 3

    for attempt in range(max_retries):
        self.signed_header = self._sign(payload_str)

        try:
            async with session.post(
                full_endpoint,
                headers={
                    **self.signed_header,
                    "Content-Type": "application/json",
                },
                data=payload_str,
            ) as req:

                body = await req.text()

                # Debug HTTP-level failures
                if req.status != 200:
                    print(
                        f"{curr_dt()}: HTTP {req.status} "
                        f"| Endpoint: {endpoint} "
                        f"| Body: {body[:500]}"
                    )

                    if attempt < max_retries - 1:
                        await asyncio.sleep(attempt + 1)
                        continue

                    return None

                # Prevent JSONDecodeError from killing the bot
                if not body.strip():
                    print(
                        f"{curr_dt()}: Empty response "
                        f"| Endpoint: {endpoint}"
                    )

                    if attempt < max_retries - 1:
                        await asyncio.sleep(attempt + 1)
                        continue

                    return None

                try:
                    response = json.loads(body)
                except json.JSONDecodeError:
                    print(
                        f"{curr_dt()}: Invalid JSON response "
                        f"| Endpoint: {endpoint} "
                        f"| Body: {body[:500]}"
                    )

                    if attempt < max_retries - 1:
                        await asyncio.sleep(attempt + 1)
                        continue

                    return None

                # Bybit API response
                if response.get("retMsg") in ("OK", "success"):

                    return {
                        "return": response.get("result"),
                        "latency": int(response["time"])
                        - int(self.timestamp),
                    }

                code = response.get("retCode")
                msg = response.get("retMsg", "Unknown error")

                print(
                    f"{curr_dt()}: {msg} "
                    f"(code={code}) "
                    f"| Endpoint: {endpoint}"
                )

                return None

        except (aiohttp.ClientError, asyncio.TimeoutError) as e:

            print(
                f"{curr_dt()}: Request error: {e} "
                f"| Endpoint: {endpoint}"
            )

            if attempt < max_retries - 1:
                await asyncio.sleep(attempt + 1)
                continue

            return None

    return None

