from asyncio import TimeoutError
from discord.errors import Forbidden, NotFound, HTTPException
from discord import Embed
from ..structures.Bloxlink import Bloxlink
from ..exceptions import CancelledPrompt, CancelCommand, Error
from ..constants import RED_COLOR, INVISIBLE_COLOR
from config import PROMPT, RELEASE, IS_DOCKER # pylint: disable=no-name-in-module

get_resolver = Bloxlink.get_module("resolver", attrs="get_resolver")
broadcast = Bloxlink.get_module("ipc", attrs="broadcast")

prompts = {}


@Bloxlink.loader
class Arguments:
	def __init__(self, _, skipped_args, CommandArgs):
		self.message = CommandArgs.message
		self.author = CommandArgs.message.author

		self.response = CommandArgs.response
		self.locale = CommandArgs.locale

		self.skipped_args = skipped_args or []


	async def say(self, text, type=None, is_prompt=True, embed=True, dm=False):
		if not embed:
			if is_prompt:
				text = f"{text}\n\n{self.locale('prompt.toCancel')}\n\n{self.locale('prompt.timeoutWarning', timeout=PROMPT['PROMPT_TIMEOUT'])}"

			return await self.response.send(text, dm=dm, no_dm_post=True)

		if type == "error":
			new_embed = Embed(title=self.locale("prompt.errors.title"))
			new_embed.colour = RED_COLOR
		else:
			new_embed = Embed(title=self.locale("prompt.title"))
			new_embed.colour = INVISIBLE_COLOR

		new_embed.description = f"{text}\n\n{self.locale('prompt.toCancel')}"
		new_embed.set_footer(text=self.locale("prompt.timeoutWarning", timeout=PROMPT["PROMPT_TIMEOUT"]))

		msg = await self.response.send(embed=new_embed, dm=dm, no_dm_post=True)

		if not msg:
			if is_prompt:
				text = f"{text}\n\n{self.locale('prompt.toCancel')}\n\n{self.locale('prompt.timeoutWarning', timeout=PROMPT['PROMPT_TIMEOUT'])}"

			return await self.response.send(text, dm=dm, no_dm_post=True)

		return msg

	@staticmethod
	def in_prompt(author):
		return prompts.get(author.id)

	async def prompt(self, arguments, skipped_args=None, error=False, return_messages=False, embed=True, dm=False):
		prompts[self.author.id] = True

		skipped_args = skipped_args or self.skipped_args
		checked_args = 0
		err_count = 0
		resolved_args = {}
		messages = []

		if dm:
			if IS_DOCKER:
				try:
					m = await self.author.send("Loading setup...")
				except Forbidden:
					dm = False
				else:
					await m.delete()
					await self.response.send("**Please check your DMs to continue.**")
			else:
				dm = False

		try:
			while checked_args != len(arguments):
				if err_count == PROMPT["PROMPT_ERROR_COUNT"]:
					raise CancelledPrompt("Too many failed attempts.", type="delete")

				prompt = arguments[checked_args]
				skipped_arg = self.skipped_args[checked_args:checked_args+1]
				skipped_arg = skipped_arg and skipped_arg[0] or None
				my_arg = skipped_arg
				message = self.message

				if prompt.get("optional") and not skipped_arg:
					resolved_args[prompt["name"]] = None
					checked_args += 1

					continue

				formatting = prompt.get("formatting", True)

				try:
					if not skipped_arg:
						try:
							if formatting:
								prompt["prompt"] = prompt["prompt"].format(**resolved_args)

							client_message = await self.say(prompt["prompt"], type=error and "error", embed=embed, dm=dm)

							if client_message:
								messages.append(client_message)

							if dm:
								message_content = await broadcast(self.author.id, type="DM")
								my_arg = message_content["0"]

								if my_arg in ("cluster offline", "cluster timeout"):
									raise Error("There's a temporary Bloxlink issue preventing this from working.\n"
												"Please try again later.")
							else:
								message = await Bloxlink.wait_for("message", check=self._check_prompt(), timeout=PROMPT["PROMPT_TIMEOUT"])
								my_arg = message.content

								messages.append(message)

							if my_arg.lower() == "cancel":
								raise CancelledPrompt(type="delete")

						except TimeoutError:
							raise CancelledPrompt(f"timeout ({PROMPT['PROMPT_TIMEOUT']}s)")

					resolver = get_resolver(prompt.get("type", "string"))
					resolved, error_message = await resolver(not dm and message, prompt, my_arg)

					if resolved:
						if prompt.get("validation"):
							res = [await prompt["validation"](content=my_arg, message=not dm and message)]

							if isinstance(res[0], tuple):
								if not res[0][0]:
									error_message = res[0][1]
									resolved = False
							else:
								if not res[0]:
									error_message = "Prompt failed validation. Please try again."
									resolved = False
					else:
						error_message = f"{self.locale('prompt.errors.invalidArgument', arg='**' + prompt.get('type', 'string') + '**')}: ``{error_message}``"

					if resolved:
						checked_args += 1
						resolved_args[prompt["name"]] = resolved
					else:
						client_message = await self.say(error_message, type="error", embed=embed, dm=dm)

						if client_message and not dm:
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
						if not dm:
							for message in messages:
								try:
									await message.delete()
								except (Forbidden, NotFound, HTTPException):
									pass

						await self.response.send("**Cancelled prompt.**", dm=dm, no_dm_post=True)

			if return_messages:
				return resolved_args, messages

			return resolved_args

		finally:
			del prompts[self.author.id]

	def _check_prompt(self):
		def wrapper(message):
			return message.author.id  == self.message.author.id and \
				   message.channel.id == self.message.channel.id

		return wrapper
