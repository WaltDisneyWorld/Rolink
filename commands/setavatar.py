from io import BytesIO
from discord.errors import NotFound, HTTPException
import aiohttp

async def fetch(session, url):
	async with session.get(url) as response:
		return await response.read(), response


async def setup(**kwargs):
	command = kwargs.get("command")
	client = kwargs.get("client")

	@command(name="setavatar", category="Developer", permissions={
		"owner_only": True
	}, aliases=["avatar"])
	async def setavatar(message, response, args, prefix):
		"""changes the bot avatar"""

		buffer = BytesIO()

		if message.attachments:

			try:
				attachment = message.attachments[0]

				await attachment.save(buffer)
				await client.user.edit(avatar=buffer.getvalue())

				await response.success("Successfully **changed** the avatar!")

			except NotFound:
				await response.error("The original attachment was deleted.")

			except HTTPException:
				await response.error("Failed to **update** the avatar.")
		else:
			try:
				async with aiohttp.ClientSession() as session:
					resp = await fetch(session, args.args[0])
					resp = resp[0]

					buffer.write(resp)

					await client.user.edit(avatar=buffer.getvalue())

					await response.success("Successfully **changed** the avatar!")

			except HTTPException:
				await response.error("Failed to **update** the avatar.")
