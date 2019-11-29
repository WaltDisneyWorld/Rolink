from ..structures.Bloxlink import Bloxlink

parse_message = Bloxlink.get_module("commands", attrs="parse_message")
in_prompt = Bloxlink.get_module("arguments", attrs="in_prompt")

@Bloxlink.module
class MessageEvent:
	def __init__(self, args):
		pass

	async def __setup__(self):

		@Bloxlink.event
		async def on_message(message):
			author = message.author

			if author.bot:
				return
			elif not message.channel:
				return
			elif in_prompt(author):
				return

			await parse_message(message)
