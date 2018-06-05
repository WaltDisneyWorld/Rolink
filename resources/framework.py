from os import listdir
from resources.module import new_module
from .settings import MODULE_DIR


client = None
loop = None


def get_files(directory:str):
	return [name for name in listdir(directory) if name[:1] != "." and name[:2] != "__"]

async def register_modules():
	"""registers and runs all modules found in specific folders"""
	for directory in MODULE_DIR:
		files = get_files(directory)
		for filename in [f.replace(".py", "") for f in files]:
			await new_module(directory, filename)


def connect(bot):
	"""connects the main point of entry to the framework"""
	global client
	global loop
	client = bot
	loop = bot.loop
	loop.create_task(register_modules())
