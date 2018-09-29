from discord import Embed
from math import floor
from time import time
from config import VERSION, OWNER_PROFILE
import psutil
import os

started = time()


async def setup(**kwargs):
	command = kwargs.get("command")
	client = kwargs.get("client")


	@command(name="stats")
	async def stats(message, response, args, prefix):
		"""shows Bloxlink stats"""

		embed = Embed()
		embed.set_author(name=client.user.name, icon_url=client.user.avatar_url)

		seconds = floor(time() - started)

		m, s = divmod(seconds, 60)
		h, m = divmod(m, 60)
		d, h = divmod(h, 24)

		days, hours, minutes, seconds = None, None, None, None


		if d:
			days = f"{d}d"
		if h:
			hours = f"{h}h"
		if m:
			minutes = f"{m}m"
		if s:
			seconds = f"{s}s"

		uptime = f"{days or ''} {hours or ''} {minutes or ''} {seconds or ''}".strip()

		process = psutil.Process(os.getpid())
		mem = floor(process.memory_info()[0] / float(2 ** 20))

		embed.add_field(name="Version", value=VERSION)
		embed.add_field(name="Owner", value=OWNER_PROFILE)
		embed.add_field(name="Servers", value=len(client.guilds))
		embed.add_field(name="Uptime", value=uptime)
		embed.add_field(name="Users", value=len(client.users))
		embed.add_field(name="Memory Usage", value=f"{mem} MB")

		await response.send(embed=embed)
