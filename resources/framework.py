from os import listdir
from resources.module import new_module


client = None
loop = None
config = None

module_dir = None

def get_files(directory:str):
	return [name for name in listdir(directory) if name[:1] != "." and name[:2] != "__"]

async def register_modules():
	"""registers and runs all modules found in specific folders"""
	for directory in module_dir:
		files = get_files(directory)
		for filename in [f.replace(".py", "") for f in files]:
			await new_module(directory, filename)


def connect(bot, settings):
	"""connects the main point of entry to the framework"""
	global client
	global loop
	global config
	global module_dir
	config = settings
	module_dir = config.MODULE_DIR
	client = bot
	loop = bot.loop
	loop.create_task(register_modules())
