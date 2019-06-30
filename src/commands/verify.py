from resources.structures.Bloxlink import Bloxlink


@Bloxlink.command
class VerifyCommand(Bloxlink.Module):
	"""link your Roblox accont to your Discord account"""

	def __init__(self):
		pass

	@staticmethod
	@Bloxlink.flags
	async def __main__(CommandArgs):
		pass

	@staticmethod
	@Bloxlink.subcommand
	async def add(CommandArgs):
		pass


