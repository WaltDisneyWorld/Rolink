from asyncio import TimeoutError
from discord.errors import Forbidden, NotFound, HTTPException
from discord import Embed
from ..structures.Bloxlink import Bloxlink # pylint: disable=import-error
from ..exceptions import CancelledPrompt, CancelCommand, Error # pylint: disable=import-error
from ..constants import RED_COLOR, INVISIBLE_COLOR # pylint: disable=import-error
from config import RELEASE # pylint: disable=no-name-in-module
from ..constants import IS_DOCKER, TIP_CHANCES, SERVER_INVITE, PROMPT # pylint: disable=import-error
import random

get_resolver = Bloxlink.get_module("resolver", attrs="get_resolver")
broadcast = Bloxlink.get_module("ipc", attrs="broadcast")

prompts = {}



class Arguments:
	def __init__(self, CommandArgs):
		self.message = CommandArgs.message
		self.author = CommandArgs.message.author

		self.response = CommandArgs.response
		self.locale = CommandArgs.locale

		self.prefix = CommandArgs.prefix

		self.messages = []
		self.dm_post = None
		self.cancelled = False
		self.dm_false_override = False
		self.skipped_args = []


	async def say(self, text, type=None, footer=None, embed_title=None, is_prompt=True, embed_color=INVISIBLE_COLOR, embed=True, dm=False):
		embed_color = embed_color or INVISIBLE_COLOR

		if self.dm_false_override:
			dm = False

		if footer:
			footer = f"{footer}\n"
		else:
			footer = ""

		if not embed:
			if is_prompt:
				text = f"{text}\n\n{footer}{self.locale('prompt.toCancel')}\n\n{self.locale('prompt.timeoutWarning', timeout=PROMPT['PROMPT_TIMEOUT'])}"

			return await self.response.send(text, dm=dm, no_dm_post=True)

		description = f"{text}\n\n{footer}{self.locale('prompt.toCancel')}"

		if type == "error":
			new_embed = Embed(title=embed_title or self.locale("prompt.errors.title"))
			new_embed.colour = RED_COLOR

			show_help_tip = random.randint(1, 100)

			if show_help_tip <= TIP_CHANCES["PROMPT_ERROR"]:
				description = f"{description}\n\nExperiencing issues? Our [Support Server]({SERVER_INVITE}) has a team of Helpers ready to help you if you're having trouble!"
		else:
			new_embed = Embed(title=embed_title or self.locale("prompt.title"))
			new_embed.colour = embed_color

		new_embed.description = description

		new_embed.set_footer(text=self.locale("prompt.timeoutWarning", timeout=PROMPT["PROMPT_TIMEOUT"]))

		msg = await self.response.send(embed=new_embed, dm=dm, no_dm_post=True)

		if not msg:
			if is_prompt:
				text = f"{text}\n\n{self.locale('prompt.toCancel')}\n\n{self.locale('prompt.timeoutWarning', timeout=PROMPT['PROMPT_TIMEOUT'])}"

			return await self.response.send(text, dm=dm, no_dm_post=True)

		if msg and not dm:
			self.messages.append(msg.id)

		return msg


	@staticmethod
	def in_prompt(author):
		return prompts.get(author.id)

	async def prompt(self, arguments, error=False, embed=True, dm=False, no_dm_post=False):
		prompts[self.author.id] = True

		checked_args = 0
		err_count = 0
		resolved_args = {}
		had_args = {x:True for x, y in enumerate(self.skipped_args)}

		if dm:
			if IS_DOCKER:
				try:
					m = await self.author.send("Loading setup...")
				except Forbidden:
					dm = False
				else:
					try:
						await m.delete()
					except NotFound:
						pass

					if not no_dm_post:
						self.dm_post = await self.response.send(f"{self.author.mention}, **please check your DMs to continue.**")
			else:
				dm = False

		try:
			while checked_args != len(arguments):
				if err_count == PROMPT["PROMPT_ERROR_COUNT"]:
					raise CancelledPrompt("Too many failed attempts.", type="delete")

				prompt = arguments[checked_args]
				skipped_arg = self.skipped_args and self.skipped_args[0]
				message = self.message

				if prompt.get("optional") and not had_args.get(checked_args):
					resolved_args[prompt["name"]] = None
					checked_args += 1

					continue

				formatting = prompt.get("formatting", True)
				prompt_text = prompt["prompt"]

				if not skipped_arg:
					try:
						if formatting:
							prompt_text = prompt_text.format(**resolved_args, prefix=self.prefix)

						await self.say(prompt_text, embed_title=prompt.get("embed_title"), embed_color=prompt.get("embed_color"), footer=prompt.get("footer"), type=error and "error", embed=embed, dm=dm)

						if dm and IS_DOCKER:
							message_content = await broadcast(self.author.id, type="DM", send_to=f"{RELEASE}:CLUSTER_0", waiting_for=1, timeout=PROMPT["PROMPT_TIMEOUT"])
							skipped_arg = message_content[0]

							if not skipped_arg:
								await self.say("Cluster which handles DMs is temporarily unavailable. Please say your message in the server instead of DMs.", type="error", embed=embed, dm=dm)
								self.dm_false_override = True
								dm = False

								message = await Bloxlink.wait_for("message", check=self._check_prompt(), timeout=PROMPT["PROMPT_TIMEOUT"])

								skipped_arg = message.content

								if prompt.get("delete_original", True):
									self.messages.append(message.id)

							if skipped_arg == "cluster timeout":
								skipped_arg = "cancel (timeout)"

						else:
							message = await Bloxlink.wait_for("message", check=self._check_prompt(dm), timeout=PROMPT["PROMPT_TIMEOUT"])

							skipped_arg = message.content

							if prompt.get("delete_original", True):
								self.messages.append(message.id)

						skipped_arg_lower = skipped_arg.lower()
						if skipped_arg_lower == "cancel":
							raise CancelledPrompt(type="delete", dm=dm)
						elif skipped_arg_lower == "cancel (timeout)":
							raise CancelledPrompt(f"timeout ({PROMPT['PROMPT_TIMEOUT']}s)", dm=dm)

					except TimeoutError:
						raise CancelledPrompt(f"timeout ({PROMPT['PROMPT_TIMEOUT']}s)", dm=dm)

				skipped_arg_lower = skipped_arg.lower()

				if skipped_arg_lower in prompt.get("exceptions", []):
					checked_args += 1
					resolved_args[prompt["name"]] = skipped_arg_lower

					continue

				resolver_types = prompt.get("type", "string")

				if not isinstance(resolver_types, list):
					resolver_types = [resolver_types]

				resolve_errors = []
				resolved = False
				error_message = None

				for resolver_type in resolver_types:
					resolver = get_resolver(resolver_type)
					resolved, error_message = await resolver(message, prompt, skipped_arg)

					if resolved:
						if prompt.get("validation"):
							res = [await prompt["validation"](content=skipped_arg, message=not dm and message)]

							if isinstance(res[0], tuple):
								if not res[0][0]:
									error_message = res[0][1]
									resolved = False

							else:
								if not res[0]:
									error_message = "Prompt failed validation. Please try again."
									resolved = False

							if resolved:
								resolved = res[0]
					else:
						error_message = f"{self.locale('prompt.errors.invalidArgument', arg='**' + resolver_type + '**')}: ``{error_message}``"

					if error_message:
						resolve_errors.append(error_message)
					else:
						break

				if resolved:
					checked_args += 1
					resolved_args[prompt["name"]] = resolved
				else:
					await self.say("\n".join(resolve_errors), type="error", embed=embed, dm=dm)

					try:
						self.skipped_args[checked_args] = None
						had_args[checked_args] = True
					except IndexError:
						pass

					err_count += 1

				if self.skipped_args:
					self.skipped_args.pop(0)


			return resolved_args

		finally:
			prompts.pop(self.author.id, None)


	def _check_prompt(self, dm=False):
		def wrapper(message):
			if message.author.id  == self.message.author.id:
				if dm:
					return not message.guild
				else:
					return message.channel.id == self.message.channel.id
			else:
				return False

		return wrapper