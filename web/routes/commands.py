from ..api import app
from sanic.response import json
from resources.modules.commands import commands
from asyncio import sleep
from resources.modules.utils import get_files 


commands_json = None



async def get_commands():
	commands_count = len(get_files("commands"))
	commands_list = []
	while commands_count != len(commands):
		await sleep(1.0)

	for command_name, command in commands.items():
		if not command.hidden:
			commands_list.append({
				"name": command.name,
				"category": command.category,
				"description": command.description,
				"examples": command.examples,
				"args": command.usage
			})
	global commands_json
	commands_json = json(commands_list)
	return commands_json
	

@app.route("/api/v1/commands")
async def route(request):
	c = commands_json or await get_commands()
	return c
