from discord import AutoShardedClient
from os import environ as env
from resources.modules.utils import get_files
from resources.module import new_module
import config
import resources.storage as storage


if storage.get("client"):
	client = storage.client
	loop = client.loop
else:
	client = AutoShardedClient(fetch_offline_members=False)
	storage.load(client=client)

loop = client.loop



async def register_modules():
	for directory in config.MODULE_DIR:
		files = get_files(directory)
		for filename in [f.replace(".py", "") for f in files]:
			#loop.create_task(new_module(directory, filename))
			await new_module(directory, filename)

	loop.create_task(new_module("web", "api"))


if __name__ == "__main__":
	token = env.get("token") or getattr(config, "TOKEN")

	loop.create_task(register_modules())

	client.run(token)
