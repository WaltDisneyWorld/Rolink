from aiohttp import web
from core.router import routes
from core.db import load_database
import logging


async def factory():
    await load_database()

    app = web.Application()

    gunicorn_logger = logging.getLogger("gunicorn.error")
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)


    routes(app)


    return app
