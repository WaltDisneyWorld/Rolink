from ..api import app
from sanic.response import text


@app.route("/api/v1/")
async def route(request):
	return text("hello there 😄😃")
