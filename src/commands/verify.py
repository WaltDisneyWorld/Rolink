from resources.structures.Bloxlink import Bloxlink # pylint: disable=import-error
from discord.errors import Forbidden, NotFound
from discord import Embed
from resources.exceptions import Message, UserNotVerified # pylint: disable=import-error

verify_as, update_member, get_user = Bloxlink.get_module("roblox", attrs=["verify_as", "update_member", "get_user"])
get_options = Bloxlink.get_module("trello", attrs=("get_options"))

@Bloxlink.command
class VerifyCommand(Bloxlink.Module):
	"""link your Roblox accont to your Discord account"""

	def __init__(self):
		self.examples = ["add", "unlink"]

	@Bloxlink.flags
	async def __main__(self, CommandArgs):
		trello_board = CommandArgs.trello_board
		guild_data = CommandArgs.guild_data
		guild = CommandArgs.message.guild

		if CommandArgs.flags.get("add") or CommandArgs.flags.get("verify") or CommandArgs.flags.get("force"):
			await CommandArgs.response.error(f"``{CommandArgs.prefix}verify --force`` is deprecated and will be removed in a future version of Bloxlink. "
											 f"Please use ``{CommandArgs.prefix}verify add`` instead.")
		try:
			_, _, _, _, roblox_user = await update_member(
					CommandArgs.message.author,
					guild      = guild,
					guild_data = guild_data,
					roles      = True,
					nickname   = True)
		except UserNotVerified:
			await self.add(CommandArgs)
		else:
			trello_options = {}

			if trello_board:
				trello_options, _ = await get_options(trello_board)

			welcome_message = (trello_options.get("welcomeMessage", "")) or guild_data.get("welcomeMessage", f"Welcome to **{guild.name}**, "
											   											  f"{roblox_user.username}!")
			raise Message(welcome_message)

	@staticmethod
	@Bloxlink.subcommand()
	async def add(CommandArgs):
		"""link a new account to Bloxlink"""

		guild_data = CommandArgs.guild_data
		author = CommandArgs.message.author
		trello_board = CommandArgs.trello_board

		username = len(CommandArgs.string_args) >= 1 and CommandArgs.string_args[0]

		args = []

		if not username:
			args.append({
				"prompt": "What's the username of your Roblox account?",
				"type": "string",
				"name": "username"
			})

		args.append({
			"prompt": "Would you like to set this as your default Roblox account for new servers? ``yes/no``",
			"name": "default",
			"type": "choice",
			"choices": ["yes", "no"]
		})

		args, messages = await CommandArgs.prompt(args, return_messages=True)
		username = username or args["username"]

		# TODO: if groupVerify is enabled, they must join the roblox group(s) to be able to verify. bypasses the cache.
		# groupVerify = [group_ids...]

		try:
			username = await verify_as(
				CommandArgs.message.author,
				CommandArgs.message.guild,
				response = CommandArgs.response,
				primary = args["default"] == "yes",
				username = username)

		except Message as e:
			if e.type == "error":
				await CommandArgs.response.error(e)
			else:
				await CommandArgs.response.success(e)

		else:
			trello_options = {}

			if trello_board:
				trello_options, _ = await get_options(trello_board)

			welcome_message = (trello_options.get("welcomeMessage", "")) or guild_data.get("welcomeMessage", f"Welcome to **{CommandArgs.message.guild.name}**, "
											   											  f"{username}!")

			await CommandArgs.response.success(welcome_message)

			added, removed, nickname, errors, roblox_user = await update_member(
				CommandArgs.message.author,
				guild      = CommandArgs.message.guild,
				guild_data = CommandArgs.guild_data,
				roles      = True,
				nickname   = True)

			"""
			embed = Embed(title=f"Discord Profile for {roblox_user.username}")
			embed.set_author(name=str(author), icon_url=author.avatar_url, url=roblox_user.profile_link)

			if added:
				embed.add_field(name="Added Roles", value=", ".join(added))
			if removed:
				embed.add_field(name="Removed Roles", value=", ".join(removed))
			if nickname:
				embed.description = f"**Nickname:** ``{nickname}``"
			if errors:
				embed.add_field(name="Errors", value=", ".join(errors))

			embed.set_footer(text="Powered by Bloxlink", icon_url=Bloxlink.user.avatar_url)

			await CommandArgs.response.send(embed=embed)
			"""

		finally:
			messages.append(CommandArgs.message)

			for message in messages:
				try:
					await message.delete()
				except (Forbidden, NotFound):
					pass



	@staticmethod
	@Bloxlink.subcommand
	async def view(CommandArgs):
		"""view your linked account(s)"""

		raise NotImplementedError

	@staticmethod
	@Bloxlink.subcommand
	async def unlink(CommandArgs):
		"""unlink an account from Bloxlink"""

		raise NotImplementedError
