from resources.modules.roblox import clear_user_from_cache, give_roblox_stuff
from resources.modules.utils import is_premium
from asyncio import sleep

cache = []



async def cache_loop():
	while True:
		global cache
		cache = []

		await sleep(300)

async def setup(client, *args, **kwargs):
	loop = client.loop
	loop.create_task(cache_loop())
	r = kwargs.get("r")

	@client.event
	async def on_typing(channel, user, when):
		await clear_user_from_cache(author=user)

		if await is_premium(channel.guild):

			guild_data = await r.table("guilds").get(str(channel.guild.id)).run() or {}
			persist_roles = guild_data.get("persistRoles")

			if persist_roles:
				await give_roblox_stuff(user, complete=True)
