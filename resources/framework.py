from os import listdir
from resources.module import new_module
from .settings import MODULE_DIR


client = None


def get_files(directory:str):
	"""gets all files in a directory"""
	return [name for name in listdir(directory) if name != "__init__.py" and name != "__pycache__"]

def register_modules():
	"""registers and runs all modules found in specific folders"""
	for directory in MODULE_DIR:
		files = get_files(directory)
		for filename in [f.replace(".py", "") for f in files]:
			new_module(directory, filename)


def connect(bot):
	"""connects the main point of entry to the framework"""
	global client
	client = bot
	register_modules()
