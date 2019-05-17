from resources.structures.Bloxlink import Bloxlink


@Bloxlink.command
class VerifyCommand(Bloxlink.Module):
	"""link your Roblox accont to your Discord account"""

	def __init__(self):
		pass

	@Bloxlink.flags
	async def __main__(self, message, response, args, flags):
		pass

	@Bloxlink.subcommand
	async def add(self, message, response, args):
		pass


