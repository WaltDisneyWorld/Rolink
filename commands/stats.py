async def setup(**kwargs):
	command = kwargs.get("command")
	r = kwargs.get("r")

	@command(name="stats")
	async def stats(message, response, args, prefix):
		"""shows Bloxlink stats"""

		await response.send("soon:tm:")

		

