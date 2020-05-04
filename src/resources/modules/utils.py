from os import listdir
from re import compile
from ..structures import Bloxlink, DonatorProfile
from ..exceptions import RobloxAPIError, RobloxDown, RobloxNotFound
from config import PREFIX, HTTP_RETRY_LIMIT # pylint: disable=E0611
from ..constants import RELEASE
from discord.errors import NotFound, Forbidden
from discord.utils import find
from discord import Object
from aiohttp.client_exceptions import ClientOSError, ServerDisconnectedError
from time import time
from math import ceil
import asyncio

is_patron = Bloxlink.get_module("patreon", attrs="is_patron")

@Bloxlink.module
class Utils(Bloxlink.Module):
	def __init__(self):
		self.option_regex = compile("(.+):(.+)")
		self.bloxlink_server = self.client.get_guild(372036754078826496)


	async def __setup__(self):
		try:
			self.bloxlink_server = self.bloxlink_server or self.client.get_guild(372036754078826496) or await self.client.fetch_guild(372036754078826496)
		except Forbidden:
			self.bloxlink_server = None

	@staticmethod
	def get_files(directory):
		return [name for name in listdir(directory) if name[:1] != "." and name[:2] != "__" and name != "_DS_Store"]

	async def fetch(self, url, raise_on_failure=True, retry=HTTP_RETRY_LIMIT):
		try:
			async with self.session.get(url) as response:
				text = await response.text()

				if raise_on_failure:
					if response.status >= 500:
						if retry != 0:
							retry -= 1
							await asyncio.sleep(1.0)

							return await self.fetch(url, raise_on_failure=raise_on_failure, retry=retry)

						raise RobloxAPIError

					elif response.status == 400:
						raise RobloxAPIError
					elif response.status == 404:
						raise RobloxNotFound

				if text == "The service is unavailable.":
					raise RobloxDown

				return text, response

		except ServerDisconnectedError:
			if retry != 0:
				return await self.fetch(url, raise_on_failure=raise_on_failure, retry=retry-1)
			else:
				raise ServerDisconnectedError

		except ClientOSError:
			# TODO: raise HttpError with non-roblox URLs
			raise RobloxAPIError

	async def get_prefix(self, guild=None, guild_data=None, trello_board=None):
		if not guild:
			return PREFIX, None

		if RELEASE == "MAIN" and await guild.fetch_member(469652514501951518):
			return "!!", None

		if trello_board:
			List = await trello_board.get_list(lambda L: L.name == "Bloxlink Settings")

			if List:
				card = await List.get_card(lambda c: c.name[:6] == "prefix")

				if card:
					if card.name == "prefix":
						if card.desc:
							return card.desc.strip(), card

					else:
						match = self.option_regex.search(card.name)

						if match:
							return match.group(2), card



		guild_data = guild_data or await self.r.db("canary").table("guilds").get(str(guild.id)).run() or {}
		prefix = guild_data.get("prefix")

		if prefix and prefix != "!":
			return prefix, None

		return PREFIX, None


	async def validate_guild(self, guild):
		owner = guild.owner

		if not self.bloxlink_server:
			return True

		try:
			member = self.bloxlink_server.get_member(owner.id) or await self.bloxlink_server.fetch_member(owner.id)
		except NotFound:
			return False

		if member:
			if find(lambda r: r.name == "3.0 Access", member.roles):
				return True


		return False


	async def has_selly_premium(self, author, author_data):
		premium = author_data.get("premium") or {}
		expiry = premium and premium.get("expiry")
		# tier = premium and premium.get("tier", "bronze")

		if not expiry and expiry != 0:
			return False

		t = time()
		is_p = expiry == 0 or expiry > t
		days = expiry != 0 and expiry > t and ceil((expiry - t)/86400) or 0

		if is_p:
			codes_redeemed = author_data.get("redeemed", {})

			return {
				"days": days,
				"codes_redeemed": codes_redeemed,
				"pro_access": premium.get("pro")
			}
		else:
			return False


	async def has_patreon_premium(self, author, author_data):
		patron_data = await is_patron(author)

		return patron_data


	async def is_premium(self, author, author_data=None, rec=True):
		author_data = author_data or await self.r.table("users").get(str(author.id)).run() or {"id": str(author.id)}
		premium_data = author_data.get("premium") or {}

		if premium_data.get("transferTo"):
			return False, premium_data["transferTo"]
		elif premium_data.get("transferFrom") and rec:
			transfer_from = premium_data["transferFrom"]
			transferee_premium, _ = await self.is_premium(Object(id=transfer_from), None, rec=False)

			if transferee_premium:
				return transferee_premium, _


		data_patreon = await self.has_patreon_premium(author, author_data)

		if data_patreon:
			profile = DonatorProfile(author)
			profile.load_patreon(data_patreon)
			profile.add_features("premium", "pro")

			return profile, None
		else:
			data_selly = await self.has_selly_premium(author, author_data)

			if data_selly:
				profile = DonatorProfile(author)
				profile.load_selly(data_selly)

				features = ["premium"]

				if data_selly.get("pro_access"):
					features.append("pro")

				profile.add_features(*features)

				return profile, None


		return False, None
