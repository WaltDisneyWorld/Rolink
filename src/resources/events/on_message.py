from ..structures.Bloxlink import Bloxlink

parse_message = Bloxlink.get_module("commands", attrs="parse_message")

@Bloxlink.module
class MessageEvent:
	def __init__(self, args):
		pass

	async def setup(self):

		@Bloxlink.event
		async def on_message(message):
			if message.author.bot:
				return
			elif not message.channel:
				return

			await parse_message(message)
