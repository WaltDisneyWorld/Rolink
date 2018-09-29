from ..api import app
from sanic.response import text
from config import WEB
from resources.modules.utils import give_premium


@app.route("/api/v1/upvote", methods=["POST"])
async def route(request):
	auth = request.headers.get("Authorization")

	if auth == WEB["WEBHOOKS"]["DBOTS_AUTH"]:
		json = request.json

		id = json.get("user")
		duration = json.get("isWeekend") and 4 or 2

		await give_premium(id, duration=duration, code="Upvote", override=True)
	else:
		print("invalid auth", flush=True)
