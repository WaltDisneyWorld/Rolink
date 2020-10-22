from resources.structures.Bloxlink import Bloxlink # pylint: disable=import-error
from resources.exceptions import Error, RobloxNotFound, UserNotVerified, CancelCommand # pylint: disable=import-error
from resources.constants import ARROW, ORANGE_COLOR, PURPLE_COLOR # pylint: disable=import-error
from discord import Embed, Object
from discord.utils import find
from discord.errors import Forbidden, NotFound
from datetime import datetime
import re


FIELDS = [
    "trades",
    "favorite games",
    "favorite items",
    "inactivity notice",
    "description"
]

FIELDS_STR = ", ".join(FIELDS)

game_id_regex = re.compile(r"https://www.roblox.com/games/(\d+)/?")
catalog_id_regex = re.compile(r"https://www.roblox.com/catalog/(\d+)/?")

parse_message = Bloxlink.get_module("commands", attrs="parse_message")
get_game, get_catalog_item, get_user = Bloxlink.get_module("roblox", attrs=["get_game", "get_catalog_item", "get_user"])
get_inactive_role, handle_inactive_role, get_profile = Bloxlink.get_module("roblox", name_override="RobloxProfile", attrs=["get_inactive_role", "handle_inactive_role", "get_profile"])
post_event = Bloxlink.get_module("utils", attrs=["post_event"])


@Bloxlink.command
class ProfileCommand(Bloxlink.Module):
    """view someone's personal profile"""

    def __init__(self):
        self.arguments = [
            {
                "prompt": "Please specify the user to retrieve the profile of.",
                "name": "user",
                "type": "user",
                "optional": True
            }
        ]
        self.category = "Account"


    @staticmethod
    async def validate_date_of_return(message, content):
        time_now = datetime.now()

        try:
            time_delta = datetime.strptime(content, "%m-%d-%y")
        except ValueError:
            return None, "Invalid date format, must be in a ``mm-dd-yy`` format."

        if time_now > time_delta:
            return None, "Return date cannot be in the past!"


        return time_delta

    @staticmethod
    async def validate_games(message, content):
        games = content.replace(" ", "").split(",")[:3]
        favorite_games = set()

        for game in games:
            game_id = game_id_regex.search(game)

            if game_id:
                game_id = game_id.group(1)
            else:
                game_id = game

                if not game_id.isdigit():
                    raise Error(f"Unable to resolve ``{game_id}`` into a **Game ID.**")

                try:
                    game = await get_game(game_id)
                except RobloxNotFound:
                    raise Error(f"Unable to resolve ``{game_id}`` into a **Game ID.**")

            favorite_games.add(game_id)


        return favorite_games

    @staticmethod
    async def validate_items(message, content):
        items = content.replace(" ", "").split(",")[:3]
        favorite_items = set()

        for item in items:
            item_id = catalog_id_regex.search(item)

            if item_id:
                item_id = item_id.group(1)
            else:
                item_id = item

                if not item_id.isdigit():
                    raise Error(f"Unable to resolve ``{item_id}`` into a **Catalog Item ID.**")

                try:
                    item = await get_catalog_item(item_id)
                except RobloxNotFound:
                    raise Error(f"Unable to resolve ``{item_id}`` into a **Catalog Item ID.**")

            favorite_items.add(item_id)


        return favorite_items


    async def __main__(self, CommandArgs):
        response = CommandArgs.response
        message = CommandArgs.message
        author = message.author
        guild = message.guild
        prefix = CommandArgs.prefix
        user = CommandArgs.parsed_args["user"] or author

        trello_board = CommandArgs.trello_board
        guild_data = CommandArgs.guild_data

        inactive_role = await get_inactive_role(guild, guild_data, trello_board)

        #async with response.loading():
        try:
            roblox_user, _ = await get_user(author=user, guild=guild)
        except UserNotVerified:
            if user == author:
                message = CommandArgs.message
                message.content = f"{CommandArgs.prefix}verify"

                return await parse_message(message)
            else:
                raise Error(f"**{user}** is not linked to Bloxlink.")
        else:
            embed = await get_profile(author=author, user=user, roblox_user=roblox_user, prefix=prefix, inactive_role=inactive_role, guild=guild, guild_data=guild_data)

            await response.send(embed=embed)


    @Bloxlink.subcommand()
    async def change(self, CommandArgs):
        """change your public Bloxlink profile"""

        response = CommandArgs.response
        trello_board = CommandArgs.trello_board

        guild = CommandArgs.message.guild
        guild_data = CommandArgs.guild_data

        author = CommandArgs.message.author
        author_id = str(author.id)
        author_data = await self.r.db("bloxlink").table("users").get(author_id).run() or {"id": author_id}

        profile_data = author_data.get("profileData") or {}

        change_what = (await CommandArgs.prompt([
            {
                "prompt": f"Please specify the field to change: ``{FIELDS_STR}``.",
                "name": "change_what",
                "type": "choice",
                "choices": FIELDS,
                "formatting": False
            }
        ]))["change_what"]

        if change_what == "description":
            profile_value = (await CommandArgs.prompt([
                {
                    "prompt": "Please specify your new **description.** Please note that descriptions may NOT "
                              "contain Discord ToS breaking material or you may be banned from using Bloxlink!",
                    "name": "description",
                    "max": 1000,
                    "footer": "Say **clear** to clear/disable your description."
                }
            ]))["description"]

            if profile_value.lower() == "clear":
                profile_data.pop("description", None)
            else:
                profile_data["description"] = profile_value

        elif change_what == "inactivity notice":
            date_of_return = (await CommandArgs.prompt([
                {
                    "prompt": "Are you currently away? Please specify your **date of return** in this "
                              "format: ``MM-DD-YY``. For example: ``06-01-20``.",
                    "name": "date_of_return",
                    "validation": self.validate_date_of_return,
                    "exceptions": ("clear",),
                    "footer": "Say **clear** if you're currently BACK.",
                }
            ]))["date_of_return"]

            inactive_role = await get_inactive_role(guild, guild_data, trello_board)

            if isinstance(date_of_return, str) and date_of_return.lower() == "clear":
                profile_data.pop("activityNotice", None)

                await post_event(guild, guild_data, "inactivity notice", f"{author.mention} is now **back** from their leave of absence.", PURPLE_COLOR)

                await handle_inactive_role(inactive_role, author, False)
            else:
                reason = (await CommandArgs.prompt([
                    {
                        "prompt": "What's the **reason** for your inactivity?",
                        "name": "reason",
                        "footer": "Say **skip** to skip this option.",
                    }
                ]))["reason"]

                profile_data["activityNotice"] = {
                    "returnTimestamp": date_of_return.timestamp(),
                    "reason": reason.lower() != "skip" and reason
                }

                if reason.lower() != "skip":
                    await post_event(guild, guild_data, "inactivity notice", f"{author.mention} is now **away** for: ``{reason}``.", PURPLE_COLOR)
                else:
                    await post_event(guild, guild_data, "inactivity notice", f"{author.mention} is now **away**.", PURPLE_COLOR)

                await handle_inactive_role(inactive_role, author, True)


        elif change_what == "favorite games":
            favorite_games = (await CommandArgs.prompt([
                {
                    "prompt": "Here you can list at most **3 of your favorite Roblox games.** Please "
                              "say your game URLs or IDs in a **list format separated by commas.** For example: "
                              "``https://www.roblox.com/games/1271943503/Bloxlink-Verification-Game, 920587237, "
                              "https://www.roblox.com/games/370731277/MeepCity?refPageId=f4af59bc-5981-47d7-8a1a-0550ccc2b21f``",
                    "name": "favorite_games",
                    "validation": self.validate_games,
                    "exceptions": ("clear",),
                    "footer": "Say **clear** to reset all of your favorite games.",
                }
            ]))["favorite_games"]

            if isinstance(favorite_games, str) and favorite_games.lower() == "clear":
                profile_data.pop("favoriteGames", None)
            else:
                users_favorite_games = profile_data.get("favoriteGames", [])

                if len(users_favorite_games) >= 3:
                    users_favorite_games = list(favorite_games)
                else:
                    for game_id in favorite_games:
                        if not game_id in users_favorite_games:
                            users_favorite_games.append(game_id)

                users_favorite_games = users_favorite_games[:3]
                profile_data["favoriteGames"] = users_favorite_games

        elif change_what == "favorite items":
            favorite_items = (await CommandArgs.prompt([
                {
                    "prompt": "Here you can list at most **3 of your favorite Roblox catalog items.** Please "
                              "say your catalog URLs or IDs in a **list format separated by commas.** For example: "
                              "``https://www.roblox.com/catalog/5249294066/Cartoony-Rainbow-Wings, 5231646851`` ",
                    "name": "favorite_items",
                    "validation": self.validate_items,
                    "exceptions": ("clear",),
                    "footer": "Say **clear** to reset all of your favorite items.",
                }
            ]))["favorite_items"]

            if isinstance(favorite_items, str) and favorite_items.lower() == "clear":
                profile_data.pop("favoriteCatalogItems", None)
            else:
                users_favorite_items = profile_data.get("favoriteCatalogItems", [])

                if len(users_favorite_items) >= 3:
                    users_favorite_items = list(favorite_items)
                else:
                    for item_id in favorite_items:
                        if not item_id in users_favorite_items:
                            users_favorite_items.append(item_id)

                users_favorite_items = users_favorite_items[:3]
                profile_data["favoriteCatalogItems"] = users_favorite_items

        elif change_what == "trades":
            accepting_trades = (await CommandArgs.prompt([
                {
                    "prompt": "Are you currently **accepting trades?** This will show on your profile "
                              "so others may send you trades. ``Y/N``",
                    "type": "choice",
                    "choices": ["yes", "no"],
                    "name": "accepting_trades",
                    "exceptions": ("clear",),
                    "footer": "Say **clear** to clear/disable this field.",
                }
            ]))["accepting_trades"]

            if isinstance(accepting_trades, str) and accepting_trades.lower() == "clear":
                profile_data.pop("acceptingTrades", None)
            else:
                profile_data["acceptingTrades"] = accepting_trades == "yes"


        author_data["profileData"] = profile_data

        await self.r.db("bloxlink").table("users").insert(author_data, conflict="replace").run()

        await response.success(f"Successfully saved your new **{change_what}** field.")
