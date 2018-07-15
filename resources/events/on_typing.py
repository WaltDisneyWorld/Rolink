from resources.modules.roblox import clear_user_from_cache

async def setup(client, *args, **kwargs):

	@client.event
	async def on_typing(channel, user, when):
		await clear_user_from_cache(author=user)
