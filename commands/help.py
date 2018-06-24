from asyncio import sleep
from discord import Embed

from config import HELP
from resources.modules.commands import commands



async def setup(**kwargs):
	command = kwargs.get("command")

	categories = {}
	await sleep(5)
	embed = Embed(
		description=HELP
	)
	for i,v in commands.items():
		if not v.hidden and v.category.lower() != "developer":
			category = categories.get(v.category, [])
			category.append(v.name + " ➜ " + v.description)
			categories[v.category] = category

	for i,v in categories.items():
		embed.add_field(name=i, value="\n".join(v))

	@command(name="help")
	async def help_command(message, response, args):
		"""shows command usage and general help"""

		await response.send(embed=embed, dm=True, dm_post=True)
		