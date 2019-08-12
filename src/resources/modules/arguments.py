from asyncio import TimeoutError
from discord.errors import Forbidden, NotFound, HTTPException
from discord import Embed
from ..structures.Bloxlink import Bloxlink
from ..exceptions import CancelledPrompt, CancelCommand
from ..constants import RED_COLOR, INVISIBLE_COLOR
from config import PROMPT_TIMEOUT # pylint: disable=no-name-in-module

get_resolver = Bloxlink.get_module("resolver", attrs="get_resolver")

@Bloxlink.loader
class Arguments:
	def __init__(self, _, skipped_args, CommandArgs):
		self.message = CommandArgs.message

		self.response = CommandArgs.response
		self.locale = CommandArgs.locale

		self.skipped_args = skipped_args or []


	async def say(self, text, type=None, is_prompt=True, embed=True):
		if not embed:
			if is_prompt:
				text = f"{text}\n\n{self.locale('prompt.toCancel')}\n\n{self.locale('prompt.timeoutWarning', timeout=PROMPT_TIMEOUT)}"

			return await self.response.send(text)

		if type == "error":
			new_embed = Embed(title=self.locale("prompt.errors.title"))
			new_embed.colour = RED_COLOR
		else:
			new_embed = Embed(title=self.locale("prompt.title"))
			new_embed.colour = INVISIBLE_COLOR

		new_embed.description = f"{text}\n\n{self.locale('prompt.toCancel')}"
		new_embed.set_footer(text=self.locale("prompt.timeoutWarning", timeout=PROMPT_TIMEOUT))

		msg = await self.response.send(embed=new_embed)

		if not msg:
			if is_prompt:
				text = f"{text}\n\n{self.locale('prompt.toCancel')}\n\n{self.locale('prompt.timeoutWarning', timeout=PROMPT_TIMEOUT)}"

			return await self.response.send(text)

		return msg

	async def prompt(self, arguments, skipped_args=None, error=False, return_messages=False, embed=True):
		skipped_args = skipped_args or self.skipped_args
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

			formatting = prompt.get("formatting", True)

			try:
				if not skipped_arg:
					try:
						if formatting:
							prompt["prompt"] = prompt["prompt"].format(**resolved_args)

						client_message = await self.say(prompt["prompt"], type=error and "error", embed=embed)

						if client_message:
							messages.append(client_message)

						message = await Bloxlink.wait_for("message", check=self._check_prompt(), timeout=PROMPT_TIMEOUT)
						my_arg = message.content

						messages.append(message)

						if my_arg.lower() == "cancel":
							raise CancelledPrompt(type="delete")

					except TimeoutError:
						raise CancelledPrompt(f"timeout ({PROMPT_TIMEOUT}s)")

				resolver = get_resolver(prompt.get("type", "string"))
				resolved, err_msg = await resolver(message, prompt, my_arg)

				if resolved:
					checked_args += 1
					resolved_args[prompt["name"]] = resolved
				else:
					client_message = await self.say(f"{self.locale('prompt.errors.invalidArgument', arg='**' + prompt.get('type', 'string') + '**')}: ``{err_msg}``", type="error", embed=embed)

					if client_message:
						messages.append(client_message)

					try:
						self.skipped_args[checked_args] = None
					except IndexError:
						pass

					err_count += 1

			except CancelledPrompt as e:
				try:
					if e.type == "delete":
						# delete everything
						messages.append(self.message)
						raise CancelCommand
					else:
						# delete (]
						raise CancelledPrompt(e)
				finally:
					for message in messages:
						try:
							await message.delete()
						except (Forbidden, NotFound, HTTPException):
							pass

		if return_messages:
			return resolved_args, messages

		return resolved_args

	def _check_prompt(self):
		def wrapper(message):
			return message.author.id  == self.message.author.id and \
				   message.channel.id == self.message.channel.id

		return wrapper
