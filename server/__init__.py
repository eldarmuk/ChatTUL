from asyncio import AbstractEventLoop
from functools import partial
from typing import Text
from rasa.core.utils import number_of_sanic_workers
from rasa.utils.common import update_sanic_log_level
from rasa.core.run import configure_app, load_agent_on_start, close_resources, AvailableEndpoints
from sanic import Sanic, response, Request
import os
import jwt
import json
import urllib
import sqlite3 as sqlite
import logging

from .session import generate_session_id
from rasa.core.channels.socketio import SocketIOInput

logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger("socketio").setLevel(logging.DEBUG)
logging.getLogger("engineio").setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)

PRODUCTION = os.getenv('SERVER_MODE', 'dev') == 'prod'
JWT_SECRET = os.getenv('JWT_SECRET', 'devsecret')

def run():
    endpoints = AvailableEndpoints.read_endpoints("endpoints.yml")

    app = configure_app(
        cors= "*" if not PRODUCTION else "chattul.xyz",
        jwt_secret=JWT_SECRET,
        input_channels=[SocketIOInput(jwt_key=JWT_SECRET)],
        enable_api=False,
        endpoints=endpoints
    )

    @app.route("/new-session", methods=["POST"])
    async def new_session_endpoint(req: Request):
        conversation_id = generate_session_id()
        jwt_token = jwt.encode({
            'user': {
                'username': conversation_id,
                'role': "user"
            }
        }, JWT_SECRET, algorithm="HS256")

        return response.json({
                'conversation_id': conversation_id,
                'token': jwt_token
            })

    @app.route("/rate-message/<id:int>", methods=["POST"])
    async def rate_message_endpoint(req: Request, id: int):
        if len(req.body) == 0:
            return response.empty(400)
        return response.empty(501) # TODO: Not implemented

    @app.on_request
    async def authentication_middleware(req: Request):
        unauthenticated_paths = [
            "/new-session",
            "/version",
            "/",
            "/socket.io"
        ]
        if not any(req.path.startswith(path) for path in unauthenticated_paths):
            if req.headers.get("Authorization") is None or req.token is None:
                return response.empty(401)
            
            try:
                jwt.decode(req.token, JWT_SECRET, algorithms=["HS256"])
            except jwt.InvalidKeyError:
                return response.empty(401)

    async def load_model_on_start(model_archive: Text, endpoints: AvailableEndpoints, app: Sanic, loop: AbstractEventLoop):
        logger.info("Loading latest model")
        await load_agent_on_start(model_archive, AvailableEndpoints.read_endpoints("endpoints.yml"), None, app, loop)
        logger.info("Model loading finished")

    

    number_of_workers = number_of_sanic_workers(
        endpoints.lock_store if endpoints else None
    )
     
    app.register_listener(partial(load_model_on_start, "models", endpoints),"before_server_start")
    app.register_listener(close_resources, "after_server_stop")

    update_sanic_log_level()
    app.run("0.0.0.0", port=5555, debug=not PRODUCTION, workers=number_of_workers)
