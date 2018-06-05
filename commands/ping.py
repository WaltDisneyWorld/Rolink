import time

async def setup(client, command, r, *args, **kwargs):

	@command(name="ping")
	async def ping(message, response, args):
		"""measures the latency of the bot"""

		t_1 = time.perf_counter()

		await message.channel.trigger_typing()

		t_2 = time.perf_counter()

		time_delta = round((t_2-t_1)*1000)

		await message.channel.send(f'Pong! ``{time_delta}ms``')
