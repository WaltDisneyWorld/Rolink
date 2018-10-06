from discord import Embed, File
from discord.errors import Forbidden
from resources.exceptions import PermissionError, RobloxAPIError
from io import BytesIO
from discord.errors import NotFound

from resources.module import get_module
get_user = get_module("roblox", attrs=["get_user"])

import asyncio

processed = {}


async def setup(**kwargs):
	command = kwargs.get("command")
	client = kwargs.get("client")

	@command(name="bansearch", category="Premium", args = [
		{
			"name": "action",
			"prompt": "This command goes through your server ban list and tries to find " \
				"people in your server that are linked with the same account.\n\n" \
				"Would you like to **kick** ban evaders, **ban** them, or **skip** the action " \
				"(no action would be applied to them, I will only list who they are)",
			"type": "choice",
			"choices": ["skip", "ban", "kick"]

		}
	], permissions={"raw": "manage_guild"}, examples=[
		"bansearch skip -- lists ban-evaders only",
		"bansearch ban -- bans ban-evaders",
		"bansearch kick -- kicks ban-evaders"
	])
	async def bansearch(message, response, args, prefix):
		"""applies actions to users who have a banned account"""

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

		try:
			msg = await response.send("Please wait: now scanning all members.")

		except Forbidden:
			processed.pop(guild.id, None)
			raise PermissionError("I wasn't able to send a message here.") # obviously won't send, but still needed

		try:
			bans = await guild.bans()

		except Forbidden:
			raise PermissionError("I can't view the server bans; please give "
			 "me the ``Ban Members`` permission.")

		else:
			if not guild.chunked:
				async with message.channel.typing():
					await client.request_offline_members(guild)

			roblox_ids_of_banned = {}
			ban_evaders = {}
			failed = []
			successful = []

			futures = []

			async def coro1(ban):
				try:
					primary_account, accounts = await get_user(
						author=ban.user,
						guild=guild
					)

					if primary_account:
						roblox_ids_of_banned[primary_account.id] = ban.user

					for acc in accounts:
						if primary_account:
							if acc != primary_account.id:
								roblox_ids_of_banned[acc] = ban.user
						else:
							roblox_ids_of_banned[acc] = ban.user
				except RobloxAPIError:
					pass

			for ban in bans:
				#futures.append(asyncio.ensure_future(coro1(ban)))
				await coro1(ban)

			#await asyncio.gather(*futures)

			async def coro2(user):
				try:
					primary_account, accounts = await get_user(
						author=user,
						guild=guild
					)

					ban = primary_account and roblox_ids_of_banned.get(primary_account.id)

					if ban:
						ban_evaders[user] = ban
					else:
						for acc in accounts:
							ban = roblox_ids_of_banned.get(acc)
							if ban:
								ban_evaders[user] = ban
				except RobloxAPIError:
					pass

			#futures.clear()

			for user in guild.members:
				#futures.append(asyncio.ensure_future(coro2(user)))
				await coro2(user)

			#await asyncio.gather(*futures)

			if ban_evaders:
				action = args.parsed_args["action"]

				if action in ("ban", "kick"):
					if action == "ban":
						for user, ban in ban_evaders.items():
							try:
								await guild.ban(
									user=user,
									reason=f"{author} initiated {prefix}bansearch and chose to ban "
									"ban evaders.")
								successful.append(user)

							except Forbidden:
								failed.append(user)

					elif action == "kick":
						for user, ban in ban_evaders.items():
							try:
								await guild.kick(
									user=user,
									reason=f"{author} initiated {prefix}bansearch and chose to kick "
									"ban evaders.")
								successful.append(user)
							except Forbidden:
								failed.append(user)

				usernames = []
				x = 0

				for user, banned_user in ban_evaders.items():
					x += 1
					usernames.append(f"{x}.) {user} ({user.id}) - Matching banned account: {banned_user} "
					f"({banned_user.id})")

				buffer = BytesIO()
				buffer.write(bytes("\n".join(usernames), "utf-8"))

				await response.send("These members have a banned account.", files=[
					File(buffer.getvalue(), filename="ban_evaders.txt"),
				])

				action = args.parsed_args["action"]
				action = action == "kick" and "kicked" or "banned"

				if successful:
					usernames.clear()
					x = 0

					for user in successful:
						x += 1
						usernames.append(f"{x}.) {user} ({user.id})")

					buffer = BytesIO()
					buffer.write(bytes("\n".join(usernames), "utf-8"))

					await response.send(f"These members have been {action}.", files=[
						File(buffer.getvalue(), filename=f"{action}.txt"),
					])

				if failed:
					usernames.clear()
					x = 0

					for user in failed:
						x += 1
						usernames.append(f"{x}.) {user} ({user.id})")

					buffer = BytesIO()
					buffer.write(bytes("\r\n".join(usernames), "utf-8"))

					await response.send(f"These members could not be {action} (insufficient permissions).", files=[
						File(buffer.getvalue(), filename="failed.txt"),
					])

			else:
				await response.success("Hooray :tada:! There are no banned users in your server that " \
					"also have an account in your server.")

		await response.send("You may submit another full member scan in an hour.")

		try:
			await msg.delete()
		except NotFound:
			pass

		await asyncio.sleep(3600)

		processed.pop(guild.id, None)
