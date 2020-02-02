from resources.structures.Bloxlink import Bloxlink
from resources.exceptions import UserNotVerified
from discord import Embed

get_user = Bloxlink.get_module("roblox", attrs=["get_user"])


@Bloxlink.command
class GetinfoCommand(Bloxlink.Module):
	"""retrieve the Roblox information from a member"""

	def __init__(self):
		self.aliases = ["whois"]
		self.arguments = [
			{
				"prompt": "Please specify the user.",
				"type": "user",
				"name": "target",
				"optional": True
			}
		]

	@Bloxlink.flags
	async def __main__(self, CommandArgs):
		target = CommandArgs.parsed_args["target"] or CommandArgs.message.author
		flags = CommandArgs.flags

		async with CommandArgs.response.loading():
			try:
				primary_account, accounts = await get_user(*flags.keys(), author=target, send_embed=True, response=CommandArgs.response, everything=not bool(flags), basic_details=not bool(flags))
			except UserNotVerified:
				await CommandArgs.response.error(f"**{target}** is not linked to Bloxlink.")
			else:
				# TODO: let the user pick an account to switch to
				pass