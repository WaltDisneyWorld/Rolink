from asyncio import sleep
from discord import Embed

from config import HELP, OWNER, PERMISSION_MAP
from resources.modules.commands import commands

from resources.module import get_module
get_files = get_module("utils", attrs=["get_files"])



async def setup(**kwargs):
	command = kwargs.get("command")
	client = kwargs.get("client")

	commands_count = len(get_files("commands"))

	while commands_count-1 != len(commands):
		await sleep(1.0)

	@command(name="help", aliases=["cmds", "commands"])
	async def help_command(message, response, args, prefix):
		"""shows command usage and general help"""

		if args.args:
			command_name = args.args[0].lower()

			for name, command in commands.items():

				if name.lower() == command_name or command_name in command.aliases:

					command_embed = Embed(title=f"{prefix}{name}", description=command.full_description or \
						command.description)
					command_embed.set_author(name="Bloxlink", icon_url=client.user.avatar_url)

					command_embed.add_field(name="Category", value=command.category)

					if command.usage:
						command_embed.add_field(name="Usage", value=f"``{prefix}{name} {command.usage}``")
					else:
						command_embed.add_field(name="Usage", value=f"``{prefix}{name}``")

					if command.aliases:
						if len(command.aliases) > 1:
							command_embed.add_field(name="Aliases", value=", ".join(command.aliases))
						else:
							command_embed.add_field(name="Alias", value=", ".join(command.aliases))

					if command.permissions:
						permissions = []

						if command.permissions.get("raw"):
							if PERMISSION_MAP.get(command.permissions["raw"]):
								permissions.append(f'Role Permission: {PERMISSION_MAP.get(command.permissions["raw"])}')
							else:
								permissions.append(f'Role Permission: {command.permissions["raw"]}')

						if command.permissions.get("owner_only") or command.category == "Developer":
							permissions.append("Bot Developer Only: True")

						if command.category == "Premium":
							permissions.append("Premium Command")

						command_embed.add_field(name="Permissions Required", value="\n".join(permissions))

					if command.examples:
						examples = []

						for example in command.examples:
							examples.append(f"{prefix}{example}")

						command_embed.add_field(name="Examples", value=f"\n".join(examples))

					return await response.send(embed=command_embed)

			await response.error("This command does not exist.")

		else:
			embed = Embed(description=HELP)
			categories = {}

			for i,v in commands.items():
				if (v.hidden and message.author.id == OWNER) or not v.hidden:
					category = categories.get(v.category, [])
					category.append(f'``!{v.name} {v.usage}`` ➜ {v.description}')
					categories[v.category] = category

			for i,v in categories.items():
				embed.add_field(name=i, value="\n".join(v), inline=False)

			await response.send(embed=embed, dm=True)
		