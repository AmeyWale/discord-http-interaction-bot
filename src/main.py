from dotenv import load_dotenv
import uvicorn
import os
from fastapi import FastAPI, Request, Response
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from constants import (
    InteractionType,
    InteractionResponseType,
    InteractionResponseFlags,
    verify_key,
)

load_dotenv()
CLIENT_PUBLIC_KEY = os.environ.get("CLIENT_PUBLIC_KEY")


async def set_body(request: Request, body: bytes):
    async def receive():
        return {"type": "http.request", "body": body}

    request._receive = receive


async def get_body(request: Request) -> bytes:
    body = await request.body()
    await set_body(request, body)
    return body


class CustomHeaderMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        signature = request.headers["X-Signature-Ed25519"]
        timestamp = request.headers["X-Signature-Timestamp"]
        body = await get_body(request)
        if (
            signature is None
            or timestamp is None
            or not verify_key(body, signature, timestamp, CLIENT_PUBLIC_KEY)
        ):
            return Response("Bad request signature", status_code=401)
        response = await call_next(request)
        return response


app = FastAPI(middleware=[Middleware(CustomHeaderMiddleware)])


@app.post("/")
async def interactions(request: Request):
    json_data = await request.json()

    if json_data["type"] == InteractionType.PING:
        return {"type": InteractionResponseType.PONG}

    elif json_data["type"] == InteractionType.APPLICATION_COMMAND:
        if json_data["data"]["name"] == "hi":
            user_name = json_data["data"]["options"][0]["value"]
            return {
                "type": InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE,
                "data": {
                    "content": f"Hello {user_name}",
                    "flags": InteractionResponseFlags.EPHEMERAL,
                },
            }
    return {
        "type": InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE,
        "data": {
            "content": "Hello world",
        },
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3000)
