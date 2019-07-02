from asyncio import TimeoutError
from discord.errors import Forbidden
from discord import Embed
from ..structures.Bloxlink import Bloxlink
from ..exceptions import CancelledPrompt, CancelCommand
from ..constants import RED_COLOR, INVISIBLE_COLOR

get_resolver = Bloxlink.get_module("resolver", attrs="get_resolver")

@Bloxlink.loader
class Arguments:
	def __init__(self, _, skipped_args, CommandArgs):
		self.message = CommandArgs.message

		self.response = CommandArgs.response
		self.locale = CommandArgs.locale

		self.skipped_args = skipped_args or []


	async def say(self, text, type=None, is_prompt=True):
		if type == "error":
			embed = Embed(title=self.locale("prompt.errors.title"))
			embed.colour = RED_COLOR
		else:
			embed = Embed(title=self.locale("prompt.title"))
			embed.colour = INVISIBLE_COLOR

		embed.description = f"{text}\n\n{self.locale('prompt.toCancel')}"
		embed.set_footer(text=self.locale("prompt.timeoutWarning", timeout=200))

		msg = await self.response.send(embed=embed)

		if not msg:
			if is_prompt:
				text = f"{text}\n\n{self.locale('prompt.toCancel')}\n\n{self.locale('prompt.timeoutWarning')}"

			return await self.response.send(text)

		return msg

	async def prompt(self, arguments, save_messages=False):
		checked_args = 0
		resolved_args = {}
		messages = []

		while checked_args != len(arguments):
			prompt = arguments[checked_args]
			skipped_arg = self.skipped_args[checked_args:checked_args+1]
			skipped_arg = skipped_arg and skipped_arg[0] or None
			my_arg = skipped_arg
			message = self.message
			err_count = 0

			try:
				if not skipped_arg:
					try:
						client_message = await self.say(prompt["prompt"])
						message = await Bloxlink.wait_for("message", check=self.check_prompt(), timeout=200.0)
						my_arg = message.content

						if client_message:
							messages.append(client_message)

						messages.append(message)

						if my_arg.lower() == "cancel":
							raise CancelledPrompt

					except TimeoutError:
						raise CancelledPrompt("timeout (200s)")

			except CancelledPrompt as e:
				messages.append(self.message)

				for message in messages:
					try:
						await message.delete()
						message.nonce = "deleted"
					except Forbidden:
						pass

				if self.message.nonce != "deleted":
					raise CancelledPrompt(e)

				raise CancelCommand

			resolver = get_resolver(prompt.get("type", "string"))
			resolved, err_msg = await resolver(message, prompt, my_arg)

			if resolved:
				checked_args += 1
				resolved_args[prompt["name"]] = resolved
			else:
				await self.say(f"{self.locale('prompt.errors.invalidArgument', arg='**' + prompt.get('type', 'string') + '**')}: ``{err_msg}``", type="error")

				try:
					self.skipped_args[checked_args] = None
				except IndexError:
					pass

				err_count += 1

		if save_messages:
			return resolved_args, messages

		return resolved_args

	def check_prompt(self):
		def wrapper(message):
			return message.author.id  == self.message.author.id and \
				   message.channel.id == self.message.channel.id

		return wrapper
