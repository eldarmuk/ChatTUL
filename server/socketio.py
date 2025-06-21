from typing import Any, Awaitable, Callable, Dict, Optional, Text
from rasa.core.channels.channel import decode_bearer_token
from rasa.core.channels.socketio import SocketIOInput as SocketIOChannelInput, UserMessage, SocketBlueprint, SocketIOOutput as SocketIOOutputChannel
from rasa.shared.utils.io import raise_warning

from sanic import Blueprint, HTTPResponse, Request, response
from socketio import AsyncServer
import logging
import json
import asyncio

from .session import generate_session_id

logger = logging.getLogger(__name__)

class SocketIOInput(SocketIOChannelInput):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def blueprint(
        self, on_new_message: Callable[[UserMessage], Awaitable[Any]]
    ) -> Blueprint:
        """Defines a Sanic blueprint."""
        # Workaround so that socketio works with requests from other origins.
        # https://github.com/miguelgrinberg/python-socketio/issues/205#issuecomment-493769183
        sio = AsyncServer(async_mode="sanic", cors_allowed_origins=[])
        socketio_webhook = SocketBlueprint(
            sio, self.socketio_path, "socketio_webhook", __name__ # type: ignore
        )

        # make sio object static to use in get_output_channel
        self.sio = sio


        @socketio_webhook.route("/", methods=["GET"])
        async def health(_: Request) -> HTTPResponse:
            return response.json({"status": "ok"})

        async def connect(sid: Text, environ: Dict, auth: Optional[Dict]) -> bool:
            if self.jwt_key:
                jwt_payload = None
                if auth and auth.get("token"):
                    jwt_payload = decode_bearer_token(
                        auth.get("token"), self.jwt_key, self.jwt_algorithm # type: ignore
                    )

                if jwt_payload:
                    logger.debug(f"User {sid} connected to socketIO endpoint.")
                    return True
                else:
                    return False
            else:
                logger.debug(f"User {sid} connected to socketIO endpoint.")
                return True

        async def disconnect(sid: Text) -> None:
            logger.debug(f"User {sid} disconnected from socketIO endpoint.")

        async def session_request(sid: Text, data: Optional[Dict]) -> None:
            if data is None:
                data = {}
            if "session_id" not in data or data["session_id"] is None:
                data["session_id"] = generate_session_id()
            if self.session_persistence:
                await sio.enter_room(sid, data["session_id"])
            await sio.emit("session_confirm", data["session_id"], room=sid)
            logger.debug(f"User {sid} connected to socketIO endpoint.")

        async def handle_message(sid: Text, data: Dict) -> None:
            output_channel = SocketIOOutputChannel(sio, self.bot_message_evt)

            if self.session_persistence:
                if not data.get("session_id"):
                    raise_warning(
                        "A message without a valid session_id "
                        "was received. This message will be "
                        "ignored. Make sure to set a proper "
                        "session id using the "
                        "`session_request` socketIO event."
                    )
                    return
                sender_id = data["session_id"]
            else:
                sender_id = sid

            metadata = data.get(self.metadata_key, {})
            if isinstance(metadata, Text):
                metadata = json.loads(metadata)
            message = UserMessage(
                data.get("message", ""),
                output_channel,
                sender_id,
                input_channel=self.name(),
                metadata=metadata,
            )
            await on_new_message(message)


        sio.on("connect", connect, namespace=self.namespace)
        sio.on("disconnect", disconnect, namespace=self.namespace)
        sio.on("session_request", session_request, namespace=self.namespace)
        sio.on(self.user_message_evt, handle_message, namespace=self.namespace)
        
        return socketio_webhook