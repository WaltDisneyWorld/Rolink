from time import time
from math import ceil
from io import BytesIO
from discord.errors import Forbidden
from discord import File
from resources.exceptions import PermissionError
import json

async def setup(**kwargs):
	command = kwargs.get("command")
	r = kwargs.get("r")

	@command(name="requestdata", alias=["rd"])
	async def requestdata(message, response, args, prefix):
		"""requests all data that is saved under your Discord ID"""

		author = message.author

		user_data = await r.table("users").get(str(author.id)).run() or {}

		time_now = time()

		last_requested = user_data.get("lastRequestedData", 0)
		on_cooldown = last_requested > time_now
		days_left = last_requested > time_now and ceil((last_requested - time_now)/86400)

		if on_cooldown:
			await response.send("<:BloxlinkSweaty:506622933502918656> You've recently requested a copy of your data. "
			f"You may request again in **{days_left}** day{days_left > 1 and 's'}.")
		else:

			user_json = json.dumps(user_data)

			buffer = BytesIO()
			buffer.write(bytes(user_json, "utf-8"))

			try:

				await author.send("<:BloxlinkSearch:506622933012054028> Here's your data. You may request again in **30** days.",
					files=[
						File(buffer.getvalue(), filename=f"{author.id}.json"),
					]
				)

			except Forbidden:
				raise PermissionError("I was unable to DM you. Please check your privacy settings and try again.")

			else:
				last_requested = time() + (86400*30)

				await r.table("users").insert({
					"id": str(author.id),
					"lastRequestedData": last_requested
				}, conflict="update").run()

			await response.success("Check your DMs!")
