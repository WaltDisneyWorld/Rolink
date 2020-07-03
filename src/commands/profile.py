from resources.structures.Bloxlink import Bloxlink # pylint: disable=import-error
from resources.exceptions import Error, RobloxNotFound, UserNotVerified, CancelCommand # pylint: disable=import-error
from resources.constants import ARROW # pylint: disable=import-error
from discord import Embed
from datetime import datetime
import re


FIELDS = [
    "trades",
    "favorite games",
    "favorite items",
    "activity notice",
    "description"
]

FIELDS_STR = ", ".join(FIELDS)

game_id_regex = re.compile(r"https://www.roblox.com/games/(\d+)/?")
catalog_id_regex = re.compile(r"https://www.roblox.com/catalog/(\d+)/?")

parse_message = Bloxlink.get_module("commands", attrs="parse_message")
get_game, get_catalog_item, get_user = Bloxlink.get_module("roblox", attrs=["get_game", "get_catalog_item", "get_user"])

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

    async def get_profile(self, prefix, author, user, roblox_user=None):
        user_data = await self.r.table("users").get(str(user.id)).run() or {"id": str(user.id)}
        profile_data = user_data.get("profileData") or {}

        if roblox_user:
            ending = roblox_user.username.endswith("s") and "'" or "'s"
            embed = Embed(title=f"{roblox_user.username}{ending} Profile")
            embed.set_author(name=user, icon_url=user.avatar_url, url=roblox_user.profile_link)
        else:
            embed = Embed(title="Bloxlink User Profile")
            embed.set_author(name=user, icon_url=user.avatar_url)

        if not profile_data:
            if author == user:
                embed.description = f"You have no profile available! Use ``{prefix}profile change`` to make your profile."
            else:
                embed.description = f"**{user}** has no profile available."

            return embed

        description       = profile_data.get("description")
        activity_notice   = profile_data.get("activityNotice")
        favorite_games    = profile_data.get("favoriteGames")
        favorite_items    = profile_data.get("favoriteCatalogItems")
        accepting_trades  = profile_data.get("acceptingTrades")

        set_embed_desc = False

        if activity_notice:
            date = datetime.fromtimestamp(activity_notice)
            time_now = datetime.now()

            if time_now > date:
                # user is back
                profile_data.pop("activityNotice")
                user_data["profileData"] = profile_data
                await self.r.table("users").insert(user_data, conflict="replace").run()
            else:
                date_str = date.strftime("%b. %d, %Y (%A)")
                date_formatted = f"This user is currently **away** until **{date_str}.**"
                embed.description = date_formatted
                set_embed_desc = True

                # TODO: change embed color

        if accepting_trades:
            if set_embed_desc:
                embed.description = f"{embed.description}\nThis user is **accepting trades.**"
            else:
                embed.description = "This user is **accepting trades.**"

        if favorite_games:
            desc = []

            for game_id in favorite_games:
                try:
                    game = await get_game(game_id)
                except RobloxNotFound:
                    desc.append(f"**INVALID GAME:** {game_id}")
                else:
                    desc.append(f"[{game.name}]({game.url})")

            if desc:
                embed.add_field(name="Favorite Games", value="\n".join(desc))

        if favorite_items:
            desc = []

            for item_id in favorite_items:
                try:
                    catalog_item = await get_catalog_item(item_id)
                except RobloxNotFound:
                    desc.append(f"**INVALID ITEM:** {item_id}")
                else:
                    desc.append(f"[{catalog_item.name}]({catalog_item.url})")

            if desc:
                embed.add_field(name="Favorite Catalog Items", value="\n".join(desc))

        if description:
            embed.add_field(name="Personal Description", value=description, inline=False)


        if author == user:
            embed.set_footer(text=f"Use \"{prefix}profile change\" to alter your profile.")

        return embed


    async def __main__(self, CommandArgs):
        response = CommandArgs.response
        message = CommandArgs.message
        author = message.author
        guild = message.guild
        prefix = CommandArgs.prefix
        user = CommandArgs.parsed_args["user"] or author

        async with response.loading():
            try:
                roblox_user, _ = await get_user(author=user, guild=guild)
            except UserNotVerified:
                if user == author:
                    message = CommandArgs.message
                    message.content = f"{CommandArgs.prefix}verify"

                    await parse_message(message)

                    raise CancelCommand
                else:
                    raise Error(f"**{user}** is not linked to Bloxlink.")
            else:
                embed = await self.get_profile(prefix, author, user, roblox_user)

                await response.send(embed=embed)


    @Bloxlink.subcommand()
    async def change(self, CommandArgs):
        response = CommandArgs.response

        author = CommandArgs.message.author
        author_id = str(author.id)
        author_data = await self.r.table("users").get(author_id).run() or {"id": author_id}

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

        elif change_what == "activity notice":
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

            if isinstance(date_of_return, str) and date_of_return.lower() == "clear":
                profile_data.pop("activityNotice", None)
            else:
                profile_data["activityNotice"] = date_of_return.timestamp()

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

        await self.r.table("users").insert(author_data, conflict="replace").run()

        await response.success(f"Successfully saved your new **{change_what}** field.")
