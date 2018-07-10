from resources.modules.roblox import give_roblox_stuff
from asyncio import sleep

processed = {}


async def setup(**kwargs):
	command = kwargs.get("command")
	client = kwargs.get("client")

	@command(name="verifyall", category="Premium")
	async def verify(message, response, args):
		"""updates roles/nicknames for each member"""

		guild = message.guild
		author = message.author

		if processed.get(guild.id):
			entry = processed.get(guild.id)

			if entry[1] == str(author):
				return await response.error("You've recently ran a scan, please wait a little longer.")
			else:
				return await response.error(f"**{entry[1]}** recently ran a scan, please wait a little longer.")

			return

		processed[guild.id] = (True, str(author))

		if not guild.chunked:
			msg = await response.send("Please wait: loading all guild members.")
			await client.request_offline_members(guild)
			await msg.delete()

		msg = await response.send("Please wait: now updating all members.")

		for member in guild.members:
			await give_roblox_stuff(member, complete=True)

		await response.success("All done! You may submit another full member scan in an hour.")
		await msg.delete()
		await sleep(3600)

		processed.pop(guild.id, None)



