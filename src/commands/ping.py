from resources.structures.Bloxlink import Bloxlink


@Bloxlink.command
class PingCommand(Bloxlink.Module):
	"""test command"""

	def __init__(self):
		self.permissions = Bloxlink.Permissions().build(roles=["test"])
		self.aliases = ["test"]
		self.arguments = [
			{
				"prompt": "say test",
				"type": "choice",
				"name": "test1",
				"choices": ["test"]
			},
			{
				"prompt": "say 'hello how are u'",
				"type": "choice",
				"name": "test2",
				"choices": ["hello how are u"]
			},
			{
				"prompt": "say some text",
				"type": "string",
				"name": "test3"
			},
		]

	async def __main__(self, CommandArgs):
		await CommandArgs.response.send(f"Arg 1: {CommandArgs.parsed_args['test1']}")
		await CommandArgs.response.send(f"Arg 2: {CommandArgs.parsed_args['test2']}")
		await CommandArgs.response.send(f"Arg 3: {CommandArgs.parsed_args['test3']}")

	@staticmethod
	@Bloxlink.subcommand
	async def echo(CommandArgs):
		await CommandArgs.response.send("hello from a subcommand")
