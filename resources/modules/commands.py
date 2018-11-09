import traceback
import re
from config import PREFIX as default_prefix

from resources.structures.Command import Command
from resources.structures.Argument import Argument

from discord.errors import NotFound, Forbidden
from asyncio import sleep
from time import time

from resources.exceptions import RobloxAPIError, PermissionError, CancelledPrompt

from resources.module import get_module, get_loader
get_files, get_prefix, log_error = get_module("utils", attrs=["get_files", "get_prefix", "log_error"])
is_blacklisted = get_module("blacklist", attrs=["is_blacklisted"])
check_permissions = get_module("permissions", attrs=["check_permissions"])

Response = get_loader("Response", "resources.structures")



commands = dict()
commands_list = get_files("commands/")
processed_messages = []


def new_command(name=None, **kwargs):
	def wrapper(func):
		command = Command(func, name, **kwargs)
		commands[name or func.__name__] = command

	return wrapper

def new_subcommand(parent_name, name=None, **kwargs):
	def wrapper(func):
		command = Command(func, name=name or func.__name__, is_subcommand=True, **kwargs)
		parent_command = commands[parent_name]
		parent_command.add_subcommand(command)

	return wrapper

class Commands:
	def __init__(self, **kwargs):
		self.r = kwargs.get("r")
		self.client = kwargs.get("client")
		self.session = kwargs.get("session")
		self.cooldowns = {}
		self.client = kwargs.get("client")


	async def get_args(self, message, response, content="", args=None, command=None):
		if args:
			skipable_args = content.split(" | ")
		else:
			args = []
			skipable_args = []

		flags, flag_str = None, None

		if command.flags_enabled:
			flags, flag_str = Argument.parse_flags(content)

		new_args = Argument(message, args=args, response=response, command=command)
		_, is_cancelled = await new_args.call_prompt(flag_str=flag_str, skip_args=skipable_args)

		new_args.flags = flags

		return new_args, is_cancelled

	async def parse_message(self, message, guild_data=None):
		content = message.content
		channel = message.channel
		author = message.author
		guild = message.guild or (author and hasattr(author, "guild") and author.guild)

		if Argument.is_in_prompt(author):
			return

		if not guild or not author or not channel:
			return

		guild_data = guild_data or await self.r.table("guilds").get(str(guild.id)).run() or {}

		guild_prefix = await get_prefix(guild=guild, guild_data=guild_data)
		prefix = guild_prefix or default_prefix

		client_match = re.search(f"<@!?{self.client.user.id}>", content)

		check = client_match and client_match.group(0) or (content[:len(prefix)].lower() == prefix.lower() and prefix)

		if check:

			after = content[len(check):].strip()
			args = after.split(" ")
			command_name = args[0]
			del args[0]
			after = " ".join(args)

			if command_name:
				command_name = command_name.lower()

				for index, command in dict(commands).items():

					if index == command_name or command_name in command.aliases:
						time_now = time()

						if args:
							# subcommand checking
							if command.subcommands.get(args[0]):
								command = command.subcommands[args[0]]
								print(command.func, flush=True)
								del args[0]

						if command.cooldown:
							self.cooldowns[author.id] = self.cooldowns.get(author.id, {})
							self.cooldowns[author.id][command_name] = self.cooldowns[author.id].get(command_name, 0)

							if self.cooldowns[author.id][command_name] <= time_now:
								self.cooldowns[author.id][command_name] = time_now + command.cooldown
							else:
								try:
									m = await channel.send(":alarm_clock: Woah there! This command has a small cooldown.\n"
									"Please wait a few seconds and try again.")
									await sleep(3)
									await m.delete()
									await message.delete()

								except (Forbidden, NotFound):
									pass

								finally:
									return

						last_refresh = guild_data.get("lastDataRefresh")

						if not last_refresh or (last_refresh and last_refresh + 60 <= time_now):

							guild_data["lastDataRefresh"] = time_now
							guild_data["removed"] = False
							guild_data["actualId"] = str(guild.id)
							guild_data["id"] = str(guild.id)
							guild_data["name"] = guild.name
							guild_data["memberCount"] = guild.member_count
							guild_data["owner"] = {
								"username": guild.owner.name,
								"discriminator": guild.owner.discriminator,
								"avatarURL": guild.owner.avatar_url,
								"id": str(guild.owner.id)
							}

							await self.r.table("guilds").insert({
								**guild_data
							}, conflict="update").run()

						try:

							bl1 = bl2 = None
							bl1 = await is_blacklisted(author=author)

							if not bl1:
								bl2 = await is_blacklisted(guild=guild)

							if bl1 or bl2:
								try:
									await channel.send(bl1 or bl2)
								except (Forbidden, NotFound):
									pass
								finally:
									return

						except RobloxAPIError:
							pass
						except:
							pass

						processed_messages.append(message.id)

						response = Response(message=message, guild_data=guild_data, command=command_name)
						permission_success, permission_error = await check_permissions(command, channel, author)

						if permission_success:
							args, is_cancelled = await self.get_args(message, response, after, args, command)

							if not is_cancelled:
								try:
									await command.func(message, response, args, prefix)
								except NotFound:
									if not guild.chunked and not guild.unavailable:
										try:
											await channel.error("Oops! A ``NotFound`` exception was raised. We're now attempting to "\
											"fetch offline members for your server. You may retry this command after a few seconds.")
										except NotFound:
											pass
										else:
											await self.client.request_offline_members(guild)
								except Forbidden:
									await response.error("I wasn't able to participate in the channel you used this command. Please ensure "
									"I have the proper permissions for the channel/server.")
								except RobloxAPIError:
									await response.error("<:BloxlinkSad:506622933158985728> Sorry, I was unable to process your command due to a Roblox API Error. "
									"You may try again, and if this persists, Roblox may be down, or you may be supplying an invalid "
									"item to the command.")
								except PermissionError as e:
									# call post_event
									await response.error(f"Bloxlink encountered a Permission Error:\n{e}")
								except CancelledPrompt as e:
									if e.args:
										await response.send(f"**Cancelled prompt:** {e}")
									else:
										await response.send("**Cancelled prompt.**")
								except Exception as e:
									await response.error("I'm sorry, this command failed to execute. We've been "
									"sent the error message, so this problem should be fixed ASAP.")

									error = traceback.format_exc()
									await log_error(error, f'{e.__class__.__name__} from !{command_name}')

									traceback.print_exc()
						else:
							await response.error("You don't meet the required permissions: "
							f'``{permission_error}``')

						return True


	async def setup(self):
		for command_name in [f.replace(".py", "") for f in commands_list]:
			get_module(path="commands", name=command_name,
						command=new_command, subcommand=new_subcommand, 
						r=self.r, client=self.client, session=self.session
						)
		while True:
			await sleep(60)
			self.cooldowns.clear()
			processed_messages.clear()


def new_module():
	return Commands
