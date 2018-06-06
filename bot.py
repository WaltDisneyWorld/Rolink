import importlib.util
from os import environ as env
from discord import AutoShardedClient
from resources.framework import connect


config = env.get("config", "config.py")

spec = importlib.util.spec_from_file_location("config", config)
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)





client = AutoShardedClient(fetch_offline_members=False)


connect(client, config)
client.run(config.TOKEN)
