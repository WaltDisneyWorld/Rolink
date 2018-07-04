from asyncio import sleep
from discord import Embed

from config import HELP, OWNER
from resources.modules.commands import commands
from resources.modules.utils import get_files



async def setup(**kwargs):
	command = kwargs.get("command")
	client = kwargs.get("client")

	categories = {}

	commands_count = len(get_files("commands"))

	while commands_count-1 != len(commands):
		await sleep(1.0)

	@command(name="help", aliases=["cmds", "commands"])
	async def help_command(message, response, args):
		"""shows command usage and general help"""

		if args.args:
			command_name = args.args[0].lower()

			for name, command in commands.items():

				if name.lower() == command_name:

					command_embed = Embed(title=f"!{name}", description=command.description)
					command_embed.set_author(name="Bloxlink", icon_url=client.user.avatar_url)

					if command.usage:
						command_embed.add_field(name="Usage", value=f"``!{name} {command.usage}``")
					else:
						command_embed.add_field(name="Usage", value=f"``!{name}``")

					if command.aliases:
						command_embed.add_field(name="Alias", value=", ".join(command.aliases))

					if command.permissions:
						command_embed.add_field(name="Permissions Required", value=command.permissions)

					if command.examples:
						command_embed.add_field(name="Examples", value=", ".join(command.examples))

					return await response.send(embed=command_embed)

			await response.error("This command does not exist.")

		else:
			embed = Embed(description=HELP)

			for i,v in commands.items():
				if (v.hidden and message.author.id == OWNER) or not v.hidden:
					category = categories.get(v.category, [])
					category.append(v.name + " ➜ " + v.description)
					categories[v.category] = category

			for i,v in categories.items():
				embed.add_field(name=i, value="\n".join(v), inline=False)

			await response.send(embed=embed, dm=True)
		