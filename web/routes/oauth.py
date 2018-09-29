"""
from ..api import app
from sanic.response import json
from config import CLIENT_SECRET
from resources.storage import get
from jwt import encode
from base64 import b64encode
from discord import AppInfo
import aiohttp
import asyncio

loop = asyncio.get_event_loop()
client_id = AppInfo.id




url = "https://discordapp.com/api/oauth2/token"


credentials = b64encode(bytes(f"{client_id}:{CLIENT_SECRET}"))

async def encrypt(access_token):
	future = loop.run_in_executor(None, encode, {
		"access_token": access_token},
		'make this a long secret',
		algorithm='HS256'
	)

	return await future



async def oauth(code):
	async with aiohttp.ClientSession() as session:
		params = {
			"grant_type": "authorization_code",
			"code": code,
			"redirect_uri": "aaa"
		}

		headers = {
			"Authorization": f"Basic {credentials}"
		}

		async with session.post(url, params=params, headers=headers) as response:
			access_token = await response.json().get("access_token")
			access_token = await encrypt(access_token)

			return access_token


@app.route("/api/v1/oauth")
async def route(request):
	args = request.args

	if args.get("code"):
		code = args["code"][0]

		return await oauth(code)

"""