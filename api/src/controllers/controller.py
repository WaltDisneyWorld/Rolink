from views import render
from core.db import r
from core.auth import authenticate

async def index(request):
    data = "hello"

    return await render.raw(data, 200)


async def user(request):
    discord_id = request.match_info.get("id")
    guild_id   = request.query.get("guild")

    if not discord_id:
        return await render.json({
            "status": "error",
            "error": "No Discord ID specified"
        }, 400)

    user_data = await r.db("bloxlink").table("users").get(discord_id).run() or {}

    if not (user_data.get("robloxID") or user_data.get("robloxAccounts")):
        return await render.json({
            "status": "error",
            "error": "This user is not linked to Bloxlink."
        }, 200)

    primary_account = user_data.get("robloxID") and str(user_data.get("robloxID"))

    if guild_id:
        roblox_account = user_data.get("robloxAccounts", {}).get("guilds", {}).get(guild_id)
        if roblox_account:
            json_data = {
                "status": "ok",
                "primaryAccount": primary_account,
                "matchingAccount": str(roblox_account)
            }

            return await render.json(json_data, 200)
        else:
            json_data = {
                "status": "ok",
                "primaryAccount": primary_account,
                "matchingAccount": None
            }

            return await render.json(json_data, 200)

    else:
        json_data = {
            "status": "ok",
            "primaryAccount": primary_account
        }

        return await render.json(json_data, 200)


@authenticate
async def game_get(request):
    roblox_id = request.match_info.get("roblox_id")
    user_data = await r.table("gameVerification").get(roblox_id).run() or {}

    if not user_data:
        json_data = {
            "status": "error",
            "error": "User has not requested verification."
        }

    else:
         json_data = {
            "status": "ok",
            **user_data
        }

    return await render.json(json_data, 200)

@authenticate
async def game_delete(request):
    roblox_id = request.match_info.get("roblox_id")
    await r.table("gameVerification").get(roblox_id).delete().run()

    json_data = {
        "status": "ok"
    }

    return await render.json(json_data, 200)

@authenticate
async def user_verify(request):
    discord_id = request.match_info.get("discord_id")
    roblox_id = request.match_info.get("roblox_id")

    is_primary = request.query.get("primary") == "true"
    guild_id = request.query.get("guild")

    user_data = await r.db("bloxlink").table("users").get(discord_id).run() or {"id": discord_id}

    if is_primary:
        user_data["robloxID"] = roblox_id

    roblox_accounts = user_data.get("robloxAccounts", {})
    all_accounts = roblox_accounts.get("accounts", [])

    if roblox_id not in all_accounts:
        all_accounts.append(roblox_id)
        roblox_accounts["accounts"] = all_accounts

    if guild_id:
        guilds = roblox_accounts.get("guilds", {})
        guilds[guild_id] = roblox_id

        roblox_accounts["guilds"] = guilds

    user_data["robloxAccounts"] = roblox_accounts

    await r.db("bloxlink").table("users").insert(user_data, conflict="update").run()
    await r.table("gameVerification").get(roblox_id).delete().run()

    json_data = {
        "status": "ok"
    }

    return await render.json(json_data, 200)
