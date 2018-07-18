from asyncio import sleep
from discord.errors import Forbidden


async def delete_messages_from_verification_channels(r, client):
    while True:
        feed = await r.table("guilds").filter(
            lambda guild: guild.has_fields("verifyChannel")
        ).run()

        while (await feed.fetch_next()):
            guild = await feed.next()
            channel = client.get_channel(int(guild.get("verifyChannel")))

            if channel:
                try:
                    await channel.purge(limit=500)
                except Forbidden:
                    pass

        await sleep(60)


async def setup(**kwargs):
    client = kwargs.get("client")
    r = kwargs.get("r")

    loop = client.loop
    loop.create_task(delete_messages_from_verification_channels(r, client))
