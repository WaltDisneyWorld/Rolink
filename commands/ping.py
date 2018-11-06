import time

async def setup(**kwargs):
	command = kwargs.get("command")

	@command(name="ping")
	async def ping(message, response, args, prefix):
		"""measures the latency of the bot"""

		t_1 = time.perf_counter()

		await message.channel.trigger_typing()

		t_2 = time.perf_counter()
		time_delta = round((t_2-t_1)*1000)

		await response.send(f'Pong! ``{time_delta}ms``')
