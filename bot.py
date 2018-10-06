from os import environ as env
from resources.structures.Client import client
from resources.module import get_module, load_database
import config
import asyncio


loop = asyncio.get_event_loop()



async def register_modules():
	get_files = get_module("utils", attrs=["get_files"])

	for directory in config.MODULE_DIR:
		files = get_files(directory)

		for filename in [f.replace(".py", "") for f in files]:
			get_module(path=directory, name=filename)

	if config.RELEASE in ("MAIN", "LOCAL"):
		get_module(path="web", name="api")


async def main():
	await load_database()
	await register_modules()


if __name__ == "__main__":
	token = env.get("token") or getattr(config, "TOKEN")

	loop.create_task(main())

	client.run(token)
