from discord import AutoShardedClient
from resources.framework import connect
from resources.settings import TOKEN


client = AutoShardedClient(fetch_offline_members=False)


connect(client)
client.run(TOKEN)
