from resources.structures.Bloxlink import Bloxlink


@Bloxlink.command
class PingCommand(Bloxlink.Module):
	"""test command"""

	def __init__(self):
		self.permissions = {
			"roles": ["test"]
		}
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

	async def __main__(self, message, response, args):
		await response.send(f"Arg 1: {args.parsed_args['test1']}")
		await response.send(f"Arg 2: {args.parsed_args['test2']}")
		await response.send(f"Arg 3: {args.parsed_args['test3']}")

	@staticmethod
	@Bloxlink.subcommand
	async def echo(message, response, args):
		await response.send("hello from a subcommand")
