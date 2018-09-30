import asyncio
import re
from bot import client
from config import MAX_RETRIES
from discord.errors import Forbidden, NotFound, DiscordException
from discord import Embed
from resources.exceptions import RobloxAPIError

from resources.module import get_module
get_resolver = get_module("resolver", attrs=["get_resolver"])

in_prompts = {}


class Argument:
	def __init__(self, message, args, command):
		self.message = message
		self.channel = message.channel
		self.author = message.author
		self.guild = message.guild

		self.args = args
		self.parsed_args = {}
		self.checked_args = {}
		self.command = command

	@staticmethod
	def is_in_prompt(author):
		if in_prompts.get(author.id):
			return True

	@staticmethod
	def parse_flags(content):
		# https://stackoverflow.com/questions/50554698/easy-way-to-extract-flags-from-a-string
		flags = {m.group(1): m.group(2) or True for m in re.finditer(r"--?(\w+)(?: ([^-]*)|$)", content)}

		if flags:
			try:
				content = content[content.index("--"):]
			except ValueError:
				try:
					content = content[content.index("-"):]
				except ValueError:
					return {}, ""

		return flags, flags and content or ""

	@staticmethod
	async def say_message(channel, message, type="Success"):
		if type == "Success":
			embed = Embed(title="Prompt", description=f"{message}\n\nSay **cancel** to cancel.")
			embed.colour = 0x36393E
			#embed.set_footer(text="Say 𝐜𝐚𝐧𝐜𝐞𝐥 to cancel.")
		else:
			embed = Embed(title="Prompt Error", description=f"{message}\n\nTry again, or say **cancel** to cancel.")
			embed.colour = 0xE74C3C
			#embed.set_footer(text="Try again, or say 𝐜𝐚𝐧𝐜𝐞𝐥 to cancel.")
		try:
			await channel.send(embed=embed)
		except Forbidden:
			try:
				await channel.send(f"{message}\n\nTry again, or say **cancel** to cancel.")
			except Forbidden:
				pass


	@staticmethod
	async def validate_prompt(message, arg, argument_class, parsed_args, skipped_arg=None, flag_str=None):
		err_msg = None

		allow = arg.get("allow") or arg.get("allowed") or arg.get("exclude") or []

		if skipped_arg:

			if arg.get("arg_len"):
				args = skipped_arg.split(" ")
				skipped_arg = args[0:arg["arg_len"]]
				skipped_arg = " ".join(skipped_arg)

			if flag_str and skipped_arg.endswith(flag_str):
				skipped_arg = skipped_arg.rstrip(flag_str).strip()

			resolver = get_resolver(arg.get("type", "string"))

			if skipped_arg in allow:
				resolved = skipped_arg
			else:
				resolved, err_msg = await resolver(message, arg=arg, content=skipped_arg)

		else:
			content = message.content.rstrip(flag_str).strip()

			if arg.get("arg_len"):
				args = content.split(" ")
				content = args[0:arg["arg_len"]]
				content = " ".join(content)

				if argument_class:
					argument_class.args = []
					for arg1 in args:
						argument_class.args.append(arg1)

			if content.lower() == "cancel":
				return False, True

			if content in allow:
				resolved = content
			else:
				resolver = get_resolver(arg.get("type", "string"))
				resolved, err_msg = await resolver(message, arg=arg, content=content)

		if resolved or resolved is 0:

			if arg.get("check"):

				success, err_msg = await arg["check"](message, resolved, parsed_args)
				argument_class.checked_args[arg["name"]] = success

			else:
				success = True
		else:
			success = False

		if not success:
			if err_msg:
				desc = f'Invalid **{arg.get("type", "string")}** argument: ``{err_msg}.``'
				await Argument.say_message(message.channel, desc, type="Error")
				#await message.channel.send(f'Invalid **{arg.get("type", "string")}** argument: ``{err_msg}.`` ' \
				#	"Try again or say **cancel** to cancel.")
			else:
				desc = f'Invalid **{arg.get("type", "string")}** argument.'
				await Argument.say_message(message.channel, desc, type="Error")

		return (success and resolved), False

	def check_prompt(self):
		def wrapper(message):
			return message.author.id == self.message.author.id \
				and message.channel.id == self.channel.id
		return wrapper

	async def call_prompt(self, args=None, flag_str=None, skip_args=None):
		try:

			using_args = args or self.command.arguments
			parsed_args = {}

			ctr = 0

			while ctr < len(using_args):
				skipped_arg = None
				failed = 0
				arg = using_args[ctr]

				if skip_args:
					try:
						skipped_arg = skip_args[ctr]
					except IndexError:
						pass

				if skipped_arg:
					resolved, _ = await Argument.validate_prompt(self.message, arg, flag_str=flag_str, skipped_arg=skipped_arg, argument_class=self, parsed_args=parsed_args)
				
					if resolved and resolved is not 0:
						ctr += 1
						parsed_args[arg["name"]] = resolved
					else:
						success = False
						failed += 1
					
						if failed > MAX_RETRIES:
							in_prompts[self.author.id] = None
							
							await self.channel.send("**Cancelled prompt:** too many invalid arguments.")
							return None, "too many invalid prompts" 
						while not success:
							in_prompts[self.author.id] = True
							
							desc = arg["prompt"].format(**parsed_args)
							await Argument.say_message(self.channel, desc)
							#await self.channel.send(arg["prompt"].format(
							#	**parsed_args
							#) + "\nSay **cancel** to cancel.")
							
							try:
								msg = await client.wait_for("message", check=Argument.check_prompt(self), timeout=200.0)
								resolved, is_cancelled = await Argument.validate_prompt(msg, arg, argument_class=self, parsed_args=parsed_args)

								if resolved or resolved is 0:
									ctr += 1
									success = True
									parsed_args[arg["name"]] = resolved
									in_prompts[self.author.id] = None

								else:
									failed += 1
									
									if is_cancelled:
										in_prompts[self.author.id] = None
										await self.channel.send("**Cancelled prompt.**")
										return None, "user cancellation"
									elif failed > MAX_RETRIES:
										in_prompts[self.author.id] = None
										await self.channel.send("**Cancelled prompt:** too many invalid arguments.")
										return None, "user cancellation"

							except asyncio.TimeoutError:
								in_prompts[self.author.id] = None

								if self.channel:
									try:
										await self.channel.send("**Cancelled prompt:** timeout reached (200s)")
									except DiscordException:
										pass

								return None, "timeout reached"
				else:
					if arg.get("optional"):
						ctr += 1
						in_prompts[self.author.id] = None
						continue
					in_prompts[self.author.id] = True
					if arg.get("ignoreFormatting"):
						desc = arg["prompt"]
						await Argument.say_message(self.channel, desc)
						#await self.channel.send(f'{arg["prompt"]}\nSay **cancel** to cancel.')
					else:
						desc = arg["prompt"].format(**parsed_args)
						await Argument.say_message(self.channel, desc)

						#await self.channel.send(arg["prompt"].format(
						#	**parsed_args
						#) + "\nSay **cancel** to cancel.")
					try:
						msg = await client.wait_for("message", check=Argument.check_prompt(self), timeout=200.0)
						resolved, is_cancelled = await Argument.validate_prompt(msg, arg, argument_class=self, parsed_args=parsed_args)

						if resolved or resolved is 0:
							ctr += 1
							in_prompts[self.author.id] = None
							parsed_args[arg["name"]] = resolved

						elif is_cancelled:
							in_prompts[self.author.id] = None
							await self.channel.send("**Cancelled prompt.**")
							return None, "user cancellation"

					except asyncio.TimeoutError:
						await self.channel.send("**Cancelled prompt:** timeout reached (200s)")
						in_prompts[self.author.id] = None
						return None, "timeout reached"

			if not args:
				self.parsed_args = parsed_args

			in_prompts[self.author.id] = None

			return parsed_args, None

		except NotFound:
			if not self.guild.chunked:
				await client.request_offline_members(self.guild)
				return None, "**Cancelled prompt:** member not cached. Now attempting to load all members."

		except Forbidden:
			return None, "**Cancelled prompt:** please ensure I have the correct permissions."

		except RobloxAPIError:
			return None, "**Cancelled prompt:** Roblox API error"

		finally:
			in_prompts[self.author.id] = None

