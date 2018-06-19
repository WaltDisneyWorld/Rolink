from os import listdir
from resources.modules.roblox import get_user

r = None


async def get_nickname(author, guild=None, roblox_user=None, guild_data=None):
	guild = guild or author.guild
	roblox_user = roblox_user or await get_user(author=author)
	if isinstance(roblox_user, tuple):
		roblox_user = roblox_user[0]

	if roblox_user:
		await roblox_user.fill_missing_details()
		if roblox_user.is_verified:
			guild_data = await r.table("guilds").get(str(guild.id)).run() or {}
			template = guild_data.get("nicknameTemplate")

			if not template:
				return

			group_rank, clan_tag = "Guest", ""

			if "{group-rank}" in template:
				group = roblox_user.groups.get(guild_data.get("groupID","0"))
				if group:
					group_rank = group.user_role

			if "{clan-tag}" in template:
				user_data = await r.table("users").get(str(author.id)).run() or {}
				clan_tags = user_data.get("clanTags", {})
				clan_tag = clan_tags.get(str(guild.id), "")

			return template.replace(
				"{roblox-name}", roblox_user.username
			).replace(
				"{roblox-id}", roblox_user.id
			).replace(
				"{discord-name}", author.name
			).replace(
				"{discord-nick}", author.display_name
			).replace(
				"{group-rank}", group_rank
			).replace(
				"{clan-tag}", f'[{clan_tag.upper()}]'
			)

def get_files(directory:str):
	return [name for name in listdir(directory) if name[:1] != "." and name[:2] != "__"]



async def setup(**kwargs):
	global r
	r = kwargs.get("r")
