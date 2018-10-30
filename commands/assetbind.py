from json import loads
from resources.exceptions import RobloxAPIError

from resources.module import get_module
is_premium, fetch = get_module("utils", attrs=["is_premium", "fetch"])


async def setup(**kwargs):
	command = kwargs.get("command")
	r = kwargs.get("r")

	@command(name="assetbind", category="Binds", permissions={
		"raw": "manage_guild"
	}, arguments=[
		{
			"prompt": "Please say the asset ID of the bind. You can find this at the end of the URL. It should " \
			"just be numbers.",
			"type": "number",
			"name": "asset"
		},
		{
			"prompt": "Please specify either the **name or ID** of a **role** in your server " \
				"that you would like to use for this bind. A new role will be created if it doesn't " \
				"already exist.",
			"type": "role",
			"name": "role"
		}
	], examples=[
		"assetbind",
		"assetbind 1337 | gamepass owners"
	])
	async def assetbind(message, response, args, prefix):
		"""binds a role for owners of the asset"""

		guild = message.guild

		role = args.parsed_args["role"]

		guild_id = str(guild.id)
		asset_id = str(args.parsed_args["asset"])

		asset_type = "Asset"

		async with message.channel.typing():
			try:
				# is this a gamepass?
				web_response = await fetch(f'https://api.roblox.com/marketplace/game-pass-product-info?gamePassId={asset_id}')
				web_response = loads(web_response[0])

				if web_response.get("errors"):
					raise RobloxAPIError

				asset_type = "GamePass"

			except RobloxAPIError:
				# item is not a gamepass, so it must be a badge or asset
				web_response = await fetch(f"https://api.roblox.com/Marketplace/ProductInfo?assetId={asset_id}")
				web_response = loads(web_response[0])

				if web_response.get("ProductType") == "User Product":
					asset_type = "Asset"
				else:
					asset_type = "Badge"

		role_binds = (await r.table("guilds").get(guild_id).run() or {}).get("roleBinds") or {}
		virtual_groups = role_binds.get("virtualGroups", {})
		asset_bind = virtual_groups.get("assetBind", {})
		more_data = asset_bind.get("moreData", {})
		asset = more_data.get(asset_id, {})

		roles = asset.get("roles", [])
		roles.append(str(role.id))

		asset["type"] = asset_type

		asset["roles"] = roles
		more_data[asset_id] = asset
		asset_bind["moreData"] = more_data
		virtual_groups["assetBind"] = asset_bind
		role_binds["virtualGroups"] = virtual_groups

		await r.table("guilds").insert({
			"id": guild_id,
			"roleBinds": role_binds
		}, conflict="update").run()

		await response.success(f"Successfully **bounded** role **{role}** to this asset bind.")
