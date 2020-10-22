from resources.structures.Bloxlink import Bloxlink # pylint: disable=import-error
from resources.exceptions import Error, RobloxNotFound # pylint: disable=import-error
from discord import Embed
from discord.errors import NotFound

get_user = Bloxlink.get_module("roblox", attrs=["get_user"])


@Bloxlink.command
class ReverseSearchCommand(Bloxlink.Module):
    """find Discord IDs in your server that are linked to a certain Roblox ID"""

    def __init__(self):
        self.examples = ["1", "569422833", "blox_link"]
        self.arguments = [{
            "prompt": "Please specify either a username or Roblox ID. If the person's name is all numbers, "
                      "then attach a ``--username`` flag to this command. Example: ``!getinfo 1234 --username`` will "
                      "search for a user with a Roblox username of '1234' instead of a Roblox ID.",
            "name": "target"
        }]
        self.category = "Administration"
        self.permissions = Bloxlink.Permissions().build("BLOXLINK_MANAGER")

    @Bloxlink.flags
    async def __main__(self, CommandArgs):
        guild = CommandArgs.message.guild
        target = CommandArgs.parsed_args["target"]
        flags = CommandArgs.flags
        response = CommandArgs.response

        username = ID = False

        if "username" in flags:
            username = True
        elif target.isdigit():
            ID = True
        else:
            username = True

        #async with response.loading():
        try:
            account, _ = await get_user(username=username and target, roblox_id=ID and target)
        except RobloxNotFound:
            raise Error("This Roblox account doesn't exist.")
        else:
            roblox_id = account.id

            discord_ids = (await self.r.db("bloxlink").table("robloxAccounts").get(roblox_id).run() or {}).get("discordIDs")

            results = []

            if discord_ids:
                for discord_id in discord_ids:
                    try:
                        user = await guild.fetch_member(int(discord_id))
                    except NotFound:
                        pass
                    else:
                        results.append(f"{user.mention} ({user.id})")


            embed = Embed(title=f"Reverse Search for {account.username}")
            embed.set_thumbnail(url=account.avatar)


            if results:
                embed.description = "\n".join(results)
            else:
                embed.description = "No results found."

            await response.send(embed=embed)
