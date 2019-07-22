from resources.structures.Bloxlink import Bloxlink
from discord import Embed

get_user = Bloxlink.get_module("roblox", attrs=["get_user"])


@Bloxlink.command
class GetinfoCommand(Bloxlink.Module):
	"""retrieves the Roblox information from a member"""

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
		target = CommandArgs.parsed_args["target"]
		flags = CommandArgs.flags

		async with CommandArgs.response.loading():
			primary_account, _ = await get_user(*flags.keys(), author=target, send_embed=True, response=CommandArgs.response, everything=not bool(flags), basic_details=not bool(flags))

			if not primary_account:
				await CommandArgs.response.error(f"**{target}** is not linked to Bloxlink.")
