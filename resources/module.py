from .structures import Module

loaded_modules = {}


async def new_module(file_path, file_name, *args, **kwargs):
	module = loaded_modules.get(file_path+file_name)
	if module:
		return module
	else:
		module = Module(file_path, file_name, *args, **kwargs)
		loaded_modules[file_path+file_name] = module
		await module.execute()
		return module
