from discord.errors import NotFound
from resources.exceptions import PermissionError, RobloxAPIError
import asyncio

from resources.module import get_module
give_roblox_stuff = get_module("roblox", attrs=["give_roblox_stuff"])

processed = {}


async def setup(**kwargs):
	command = kwargs.get("command")
	client = kwargs.get("client")

	@command(name="verifyall", category="Premium", permissions={
		"raw": "manage_guild", "exceptions": {"roles": "Bloxlink Updater"}})
	async def verify(message, response, args, prefix):
		"""updates roles/nicknames for each member"""

		guild = message.guild
		author = message.author
		channel = message.channel

		if processed.get(guild.id):
			entry = processed.get(guild.id)

			if entry[1] == str(author):
				return await response.error("You've recently ran a scan, please wait a little longer.")
			else:
				return await response.error(f"**{entry[1]}** recently ran a scan, please wait a little longer.")

			return

		processed[guild.id] = (True, str(author))

		if not guild.chunked:
			async with channel.typing():
				await client.request_offline_members(guild)

		msg = await response.send("Please wait: now updating all members.")

		async def coro1(member):
			try:
				await give_roblox_stuff(member, complete=True)
			except PermissionError:
				pass
			except RobloxAPIError:
				processed.pop(guild.id, None)

				raise RobloxAPIError

		futures = []

		for member in guild.members:
			#futures.append(asyncio.ensure_future(coro1(member)))
			await coro1(member)

		#await asyncio.gather(*futures)

		await response.success("All done! You may submit another full member scan in an hour.")

		try:
			await msg.delete()
		except NotFound:
			pass

		await asyncio.sleep(3600)

		processed.pop(guild.id, None)
