"""
# FIXME
from asyncio import get_event_loop, ensure_future
from sanic import Sanic
from resources.storage import get
from resources.modules.utils import get_files
from resources.module import new_module
from config import WEB as web


client = get("client")
app = Sanic()

async def register_routes():
	directory = "web/routes"
	routes = get_files(directory)

	for file_name in [f.replace(".py", "") for f in routes]:
		await new_module(directory, file_name)



server = app.create_server(host=web["API"]["HOST"], port=web["API"]["PORT"])
loop = get_event_loop()
loop.create_task(register_routes())
task = ensure_future(server)
"""