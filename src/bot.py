from os import environ
import asyncio
import config
import logging
from resources.structures.Bloxlink import Bloxlink

logger = logging.getLogger()
logger.setLevel(logging.INFO)

loop = asyncio.get_event_loop()


async def register_modules():
	get_files = Bloxlink.get_module("utils", attrs="get_files")

	for directory in config.MODULE_DIR: # pylint: disable=E1101
		files = get_files(directory)

		for filename in [f.replace(".py", "") for f in files]:
			Bloxlink.get_module(path=directory, name=filename)


async def main():
	await Bloxlink.load_database()
	await register_modules()


if __name__ == "__main__":
	token = environ.get("token") or getattr(config, "TOKEN")
	loop.create_task(main())

	Bloxlink.run(token)
