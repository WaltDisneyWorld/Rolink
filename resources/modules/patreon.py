from config import PATREON, RELEASE
from resources.structures.DonatorProfile import DonatorProfile
from asyncio import sleep
from aiohttp.client_exceptions import ContentTypeError

BASE_URL = "https://www.patreon.com/api/oauth2"


class Patreon:

	def __init__(self, **kwargs):
		self.session = kwargs.get("session")
		self.loop = kwargs.get("client").loop
		self.r = kwargs.get("r")
		self.pledge_loop_started = False

		self.refresh_token = None
		self.access_token = None
		self.campaign_id = None

		self.patrons = {}

	async def setup(self):
		await self.get_patrons_from_db()
		await self.generate_token()

	async def generate_token(self):
		refresh_token = await self.r.db("patreon").table("refreshTokens").get(f"{RELEASE}_refreshToken").run() or {}

		if refresh_token:
			refresh_token = refresh_token["refreshToken"]
		else:
			refresh_token = PATREON["REFRESH_TOKEN"]

		try:

			async with self.session.post(
				f"{BASE_URL}/token",
				params={
					"grant_type": "refresh_token",
					"refresh_token": refresh_token,
					"client_id": PATREON["CLIENT_ID"],
					"client_secret": PATREON["CLIENT_SECRET"]
				}
			) as response:
				json = await response.json()

				self.access_token = json["access_token"]
				self.refresh_token = json["refresh_token"]

				await self.r.db("patreon").table("refreshTokens").insert({
					"id": f"{RELEASE}_refreshToken",
					"refreshToken": self.refresh_token
				}, conflict="update").run()

				await self.load_pledges()
				await sleep(1728000)

				await self.generate_token()

		except ContentTypeError:
			self.patrons = self.patrons or await self.get_patrons_from_db()
			await sleep(500)

			return await self.generate_token()

	async def load_pledges(self, url="{BASE_URL}/api/campaigns/{campaign_id}/pledges?include=patron.null"):
		url = url.format(BASE_URL=BASE_URL, campaign_id=await self.get_campaign_id())

		if not self.pledge_loop_started:
			self.pledge_loop_started = True
			self.loop.create_task(self.load_pledges_loop())

		try:
			async with self.session.get(
				url,
				headers={
					"Authorization": f"Bearer {self.access_token}"
				}
			) as response:
				json = await response.json()

				for patron in json["data"]:
					if not patron["attributes"].get("declined_since"):
						if patron["attributes"]["amount_cents"] >= 300:
							patron_id = patron["relationships"]["patron"]["data"]["id"]

							for extra_info in json["included"]:

								if extra_info["id"] == patron_id:
									discord = extra_info["attributes"]["social_connections"].get("discord")

									if discord:
										discord_id = discord["user_id"]

										self.patrons[discord_id] = {
											"payment": patron,
											"social": extra_info
										}

										await self.r.db("patreon").table("patrons").insert({
											"id": discord_id,
											"payment": patron,
											"social": extra_info
										}, conflict="update").run()

				if json.get("links", {}).get("next"):
					await self.load_pledges(json.get("links", {}).get("next"))

		except ContentTypeError:
			self.patrons = self.patrons or await self.get_patrons_from_db()
			await sleep(500)

			return await self.load_pledges()

	async def get_campaign_id(self):
		if self.campaign_id:
			return self.campaign_id

		try:

			async with self.session.get(
				"https://www.patreon.com/api/oauth2/api/current_user/campaigns",
				headers={
					"Authorization": f"Bearer {self.access_token}"
				}
			) as response:
				json = await response.json()

				self.campaign_id = json["data"][0]["id"]
				return self.campaign_id

		except ContentTypeError:
			self.patrons = self.patrons or await self.get_patrons_from_db()
			await sleep(500)

			return await self.get_campaign_id()

	async def get_patrons_from_db(self):
		feed = await self.r.db("patreon").table("patrons").run()

		while await feed.fetch_next():
			patron = await feed.next()

			self.patrons[patron["id"]] = {
				"payment": patron["payment"],
				"social": patron["social"]
			}

	async def load_pledges_loop(self):
		while True:
			await sleep(300)
			await self.load_pledges()

	async def is_patron(self, author):
		patron = self.patrons.get(str(author.id))

		if patron:
			profile = DonatorProfile(author, True)
			profile.load_patron(patron["payment"])

			return profile
		else:
			return DonatorProfile(author, False)


def new_module():
	return Patreon
