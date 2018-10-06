import aiohttp
from config import RELEASE, DBL_TOKEN



class PostServerCount:
	def __init__(self, **kwargs):
		self.client = kwargs.get("client")

	async def post_count(self):

		if RELEASE == "MAIN":
			url = f"https://discordbots.org/api/bots/{self.client.user.id}/stats"

			headers = {"Authorization": DBL_TOKEN}
			payload = {"server_count": len(self.client.guilds)}

			async with aiohttp.ClientSession() as aioclient:
				await aioclient.post(url, data=payload, headers=headers)

def new_module():
	return PostServerCount
