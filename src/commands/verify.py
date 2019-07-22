from resources.structures.Bloxlink import Bloxlink
from discord.errors import Forbidden, NotFound
from resources.exceptions import Message

verify_as = Bloxlink.get_module("roblox", attrs="verify_as")


@Bloxlink.command
class VerifyCommand(Bloxlink.Module):
	"""link your Roblox accont to your Discord account"""

	def __init__(self):
		self.examples = ["add", "unlink"]

	@Bloxlink.flags
	async def __main__(self, CommandArgs):
		if CommandArgs.flags.get("add") or CommandArgs.flags.get("verify") or CommandArgs.flags.get("force"):
			await CommandArgs.response.error(f"``{CommandArgs.prefix}verify --force`` is deprecated and will be removed in a future version of Bloxlink. "
											 f"Please use ``{CommandArgs.prefix}verify add`` instead.")

		# check if they are linked, then welcome user to server.

		linked = False
		if not linked:
			await self.add(CommandArgs)
		else:
			# welcome the user
			pass


	@staticmethod
	@Bloxlink.subcommand()
	async def add(CommandArgs):
		"""link a new account to Bloxlink"""

		guild_data = CommandArgs.guild_data

		username = len(CommandArgs.string_args) >= 1 and CommandArgs.string_args[0]

		args = []

		if not username:
			args.append({
				"prompt": "What's the username of your Roblox account?",
				"type": "string",
				"name": "username"
			})

		args.append({
			"prompt": "Would you like to set this as your default Roblox account for new servers? yes/no",
			"name": "default",
			"type": "choice",
			"choices": ["yes", "no"]
		})

		args, messages = await CommandArgs.prompt(args, return_messages=True)

		# if groupVerify is enabled, they must join the roblox group(s) to be able to verify. bypasses the cache.
		# groupVerify = [group_ids...]

		try:
			await verify_as(
				CommandArgs.message.author,
				CommandArgs.message.guild,
				response = CommandArgs.response,
				primary = args["default"] == "yes",
				username = username or args["username"])

		except Message as e:
			if e.type == "error":
				await CommandArgs.response.error(e)
			else:
				await CommandArgs.response.success(e)

		else:
			await CommandArgs.response.success(CommandArgs.guild_data.get("welcomeMessage",
											   f"Welcome to **{CommandArgs.message.guild.name}**, "
											   f"{CommandArgs.message.author.name}!"))
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

		pass

	@staticmethod
	@Bloxlink.subcommand
	async def unlink(CommandArgs):
		"""unlink an account from Bloxlink"""

		pass