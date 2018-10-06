from discord.errors import NotFound, Forbidden
from resources.exceptions import PermissionError, RobloxAPIError
import asyncio

from resources.module import get_module
get_user = get_module("roblox", attrs=["get_user"])

processed = {}


async def setup(**kwargs):
	command = kwargs.get("command")
	client = kwargs.get("client")
	r = kwargs.get("r")

	@command(name="clean", category="Premium", permissions={"raw": "manage_guild"})
	async def clean(message, response, args, prefix):
		"""kicks unverified members, or people not in the group"""

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

		msg = await response.send("Please wait: now checking all members.")

		unverified_members = []
		guests = []

		guild_data = await r.table("guilds").get(str(guild.id)).run() or {}

		group_id = None

		if guild_data.get("groupID"):
			group_id = str(guild_data.get("groupID"))



		async def scan(member):
			try:
				user, _ = await get_user(author=member, guild=guild)

				if user:
					await user.fill_missing_details()

					if group_id:
						if not user.groups.get(group_id):
							guests.append(member)
				else:
					unverified_members.append(member)

			except RobloxAPIError:
				processed.pop(guild.id, None)

				raise RobloxAPIError

		futures = []

		for member in guild.members:
			if not member.bot:
				#futures.append(asyncio.ensure_future(scan(member)))
				await scan(member)

		#await asyncio.gather(*futures)

		try:
			await msg.delete()
		except NotFound:
			pass

		parsed_args, is_cancelled = await args.call_prompt([
			{
				"name": "type",
				"prompt": f"{author.mention} Would you like to kick ``unverified`` members, or users not in the group (guests)?\n" \
					"Please specify one: ``unverified``, ``guests``",
				"type": "choice",
				"choices": ["unverified", "guests"]
			}
		])

		if not is_cancelled:
			if parsed_args["type"] == "unverified":

				if not unverified_members:
					processed.pop(guild.id, None)
					return await response.success("Woohoo! There are no unverified members on your server.")

				parsed_args, is_cancelled = await args.call_prompt([
					{
						"name": "to_kick",
						"prompt": f"This will kick **{len(unverified_members)}** members. Continue?",
						"type": "choice",
						"choices": ["yes", "no"]
					}
				])
				if not is_cancelled:
					if parsed_args["to_kick"] == "yes":
						for member in unverified_members:
							try:
								await member.kick(reason=f"{author} initiated an unverified member clean.")
							except Forbidden:
								processed.pop(guild.id, None)
								raise PermissionError(f"I was unable to kick {member}. Cleaning cancelled.")
						await response.success("Kicked all unverified members!")
					else:
						await response.send("**Cancelled clean.**")
						processed.pop(guild.id, None)
						return
				else:
					processed.pop(guild.id, None)
					return

			elif parsed_args["type"] == "guests":

				if not unverified_members:
					processed.pop(guild.id, None)
					return await response.success("Woohoo! There are no guests on your server.")

				if not guild_data.get("groupID"):
					processed.pop(guild.id, None)
					return await response.error("You must have a group ID set to kick guests.")

				parsed_args, is_cancelled = await args.call_prompt([
					{
						"name": "to_kick",
						"prompt": f"This will kick **{len(guests)}** members. Continue?",
						"type": "choice",
						"choices": ["yes", "no"]
					}
				])
				if not is_cancelled:
					if parsed_args["to_kick"] == "yes":
						for member in guests:
							try:
								await member.kick(reason=f"{author} initiated a guest clean.")
							except Forbidden:
								processed.pop(guild.id, None)
								raise PermissionError(f"I was unable to kick {member}. Cleaning cancelled.")
						await response.success("Kicked all guests!")
					else:
						await response.send("**Cancelled clean.**")
						processed.pop(guild.id, None)
						return
				else:
					processed.pop(guild.id, None)
					return

		else:
			processed.pop(guild.id, None)
			return

		await asyncio.sleep(3600)

		processed.pop(guild.id, None)
