from resources.structures.Bloxlink import Bloxlink # pylint: disable=import-error
from discord.errors import Forbidden, NotFound
from discord import Embed, Object
from os import environ as env
from resources.exceptions import Message, UserNotVerified, Error, RobloxNotFound, BloxlinkBypass, Blacklisted # pylint: disable=import-error
from resources.constants import DEFAULTS, NICKNAME_TEMPLATES, CACHE_CLEAR, TIP_CHANCES, GREEN_COLOR, ORANGE_COLOR, BROWN_COLOR, ARROW # pylint: disable=import-error
from aiotrello.exceptions import TrelloNotFound, TrelloUnauthorized, TrelloBadRequest
import random

verify_as, update_member, get_user, get_nickname, get_roblox_id, parse_accounts, unverify_member, format_update_embed = Bloxlink.get_module("roblox", attrs=["verify_as", "update_member", "get_user", "get_nickname", "get_roblox_id", "parse_accounts", "unverify_member", "format_update_embed"])
get_options = Bloxlink.get_module("trello", attrs="get_options")
is_premium, post_event = Bloxlink.get_module("utils", attrs=["is_premium", "post_event"])

try:
    from config import TRELLO
except ImportError:
    TRELLO = {
        "KEY": env.get("TRELLO_KEY"),
        "TOKEN": env.get("TRELLO_TOKEN"),
	    "TRELLO_BOARD_CACHE_EXPIRATION": 5 * 60,
	    "CARD_LIMIT": 100,
        "LIST_LIMIT": 10
    }

@Bloxlink.command
class VerifyCommand(Bloxlink.Module):
    """link your Roblox account to your Discord account and get your server roles"""

    def __init__(self):
        self.examples = ["add", "unlink", "view", "blox_link"]
        self.category = "Account"
        self.cooldown = 5
        self.aliases = ["getrole", "getroles"]


    @staticmethod
    async def validate_username(message, content):
        try:
            roblox_id, username = await get_roblox_id(content)
        except RobloxNotFound:
            return None, "There was no Roblox account found with that username. Please try again."

        return username

    @Bloxlink.flags
    async def __main__(self, CommandArgs):
        trello_board = CommandArgs.trello_board
        guild_data = CommandArgs.guild_data
        guild = CommandArgs.message.guild
        author = CommandArgs.message.author
        response = CommandArgs.response
        prefix = CommandArgs.prefix

        if CommandArgs.flags.get("add") or CommandArgs.flags.get("verify") or CommandArgs.flags.get("force"):
            await CommandArgs.response.error(f"``{CommandArgs.prefix}verify --force`` is deprecated and will be removed in a future version of Bloxlink. "
                                             f"Please use ``{prefix}verify add`` instead.")

            return await self.add(CommandArgs)

        if CommandArgs.real_command_name in ("getrole", "getroles"):
            CommandArgs.string_args = []

        username = len(CommandArgs.string_args) >= 1 and CommandArgs.string_args[0]

        if username:
            return await self.add(CommandArgs)

        donator_profile, _ = await is_premium(Object(id=guild.owner_id), guild=guild)
        premium = donator_profile.features.get("premium")

        if not premium:
            donator_profile, _ = await is_premium(author, guild=guild)
            premium = donator_profile.features.get("premium")

        trello_options = {}

        if trello_board:
            trello_options, _ = await get_options(trello_board)
            guild_data.update(trello_options)

        async with response.loading():
            try:
                added, removed, nickname, errors, roblox_user = await update_member(
                    CommandArgs.message.author,
                    guild                = guild,
                    guild_data           = guild_data,
                    roles                = True,
                    nickname             = True,
                    trello_board         = CommandArgs.trello_board,
                    author_data          = await self.r.db("bloxlink").table("users").get(str(author.id)).run(),
                    given_trello_options = True,
                    cache                = not premium,
                    response             = response)

            except BloxlinkBypass:
                raise Message("Since you have the ``Bloxlink Bypass`` role, I was unable to update your roles/nickname.", type="info")

            except Blacklisted as b:
                if str(b):
                    raise Error(f"{author.mention} is **blacklisted** for: ``{b}``.")
                else:
                    raise Error(f"{author.mention} is **blacklisted** from Bloxlink.")

            except UserNotVerified:
                await self.add(CommandArgs)
            else:
                welcome_message, embed = await format_update_embed(roblox_user, prefix, added, removed, errors, author, guild_data, premium)

                await response.send(content=welcome_message, embed=embed)


    @Bloxlink.subcommand()
    async def add(self, CommandArgs):
        """link a new account to Bloxlink"""

        author = CommandArgs.message.author
        guild = CommandArgs.message.guild

        guild_data = CommandArgs.guild_data
        trello_board = CommandArgs.trello_board
        prefix = CommandArgs.prefix

        response = CommandArgs.response

        username = len(CommandArgs.string_args) >= 1 and CommandArgs.string_args[0]

        args = []
        trello_options = {}

        if trello_board:
            trello_options, _ = await get_options(trello_board)
            guild_data.update(trello_options)

        dm_verification = guild_data.get("dmVerifications", DEFAULTS.get("dmVerifications"))

        if not username:
            args.append({
                "prompt": "What's the **username** of your Roblox account?",
                "type": "string",
                "name": "username",
                "validation": self.validate_username
            })

        args.append({
            "prompt": "Would you like to set this as your **default** Roblox account for new servers? ``yes/no``",
            "name": "default",
            "type": "choice",
            "choices": ["yes", "no"]
        })

        args = await CommandArgs.prompt(args, dm=dm_verification)
        username = username or args["username"]

        # TODO: if groupVerify is enabled, they must join the roblox group(s) to be able to verify. bypasses the cache.
        # groupVerify = [group_ids...]

        donator_profile, _ = await is_premium(Object(id=guild.owner_id), guild=guild)
        premium = donator_profile.features.get("premium")

        if not premium:
            donator_profile, _ = await is_premium(author, guild=guild)
            premium = donator_profile.features.get("premium")

        try:
            username = await verify_as(
                author,
                guild,
                response       = CommandArgs.response,
                primary        = args["default"] == "yes",
                username       = username,
                trello_options = trello_options,
                dm             = dm_verification,
                guild_data     = guild_data,
                update_user    = False)

        except Message as e:
            if e.type == "error":
                await response.error(e)
            else:
                await response.send(e)
        except Error as e:
            await response.error(e, dm=dm_verification, no_dm_post=True)
        else:
            try:
                added, removed, nickname, errors, roblox_user = await update_member(
                    author,
                    guild                = guild,
                    guild_data           = CommandArgs.guild_data,
                    roles                = True,
                    nickname             = True,
                    trello_board         = trello_board,
                    author_data          = await self.r.db("bloxlink").table("users").get(str(author.id)).run(),
                    given_trello_options = True,
                    cache                = not premium,
                    response             = response)

            except BloxlinkBypass:
                await response.info("Since you have the ``Bloxlink Bypass`` role, I was unable to update your roles/nickname; however, you were still linked to Bloxlink.", dm=True, no_dm_post=True)

                return

            except Blacklisted as b:
                if str(b):
                    raise Error(f"{author.mention} is **blacklisted** for: ``{b}``.")
                else:
                    raise Error(f"{author.mention} is **blacklisted** from Bloxlink.")


            welcome_message, embed = await format_update_embed(roblox_user, prefix, added, removed, errors, author, guild_data, premium)

            await post_event(guild, guild_data, "verification", f"{author.mention} has **verified** as ``{username}``.", GREEN_COLOR)

            await response.send(content=welcome_message, embed=embed, dm=dm_verification, no_dm_post=True)


    @Bloxlink.subcommand(permissions=Bloxlink.Permissions().build("BLOXLINK_MANAGER"))
    async def customize(self, CommandArgs):
        """customize the behavior of !verify"""

        # TODO: able to set: "forced groups"

        prefix = CommandArgs.prefix
        response = CommandArgs.response

        author = CommandArgs.message.author

        guild = CommandArgs.message.guild
        guild_data = CommandArgs.guild_data


        choice = (await CommandArgs.prompt([{
            "prompt": "Which option would you like to change?\nOptions: ``(welcomeMessage)``",
            "name": "choice",
            "type": "choice",
            "choices": ("welcomeMessage",)
        }]))["choice"]


        trello_board = CommandArgs.trello_board
        card = None

        if trello_board:
            options_trello_data, trello_binds_list = await get_options(trello_board, return_cards=True)
            options_trello_find = options_trello_data.get(choice)

            if options_trello_find:
                card = options_trello_find[1]

        if choice == "welcomeMessage":
            welcome_message = (await CommandArgs.prompt([{
                "prompt": f"What would you like your welcome message to be? This will be shown in ``{prefix}verify`` messages.\nYou may "
                          f"use these templates: ```{NICKNAME_TEMPLATES}```",
                "name": "welcome_message",
                "formatting": False,
                "max": 1500
            }]))["welcome_message"]

            if trello_board and trello_binds_list:
                try:
                    if card:
                        if card.name == choice:
                            await card.edit(name="welcomeMessage", desc=welcome_message)
                    else:
                        trello_settings_list = await trello_board.get_list(lambda L: L.name == "Bloxlink Settings") \
                                            or await trello_board.create_list(name="Bloxlink Settings")

                        await trello_settings_list.create_card(name="welcomeMessage", desc=welcome_message)

                    await trello_binds_list.sync(card_limit=TRELLO["CARD_LIMIT"])

                except TrelloUnauthorized:
                    await response.error("In order for me to edit your Trello settings, please add ``@bloxlink`` to your "
                                         "Trello board.")

                except (TrelloNotFound, TrelloBadRequest):
                    pass

            await self.r.table("guilds").insert({
                "id": str(guild.id),
                "welcomeMessage": welcome_message
            }, conflict="update").run()

        await post_event(guild, guild_data, "configuration", f"{author.mention} has **changed** the ``{choice}``.", BROWN_COLOR)

        raise Message(f"Successfully saved your new ``{choice}``!", type="success")


    @staticmethod
    @Bloxlink.subcommand()
    async def view(CommandArgs):
        """view your linked account(s)"""

        author = CommandArgs.message.author
        response = CommandArgs.response

        try:
            primary_account, accounts = await get_user("username", author=author, everything=False, basic_details=True)
        except UserNotVerified:
            raise Message("You have no accounts linked to Bloxlink!", type="silly")
        else:
            accounts = list(accounts)

            parsed_accounts = await parse_accounts(accounts, reverse_search=True)
            parsed_accounts_str = []
            primary_account_str = "No primary account set"

            for roblox_username, roblox_data in parsed_accounts.items():
                if roblox_data[1]:
                    username_str = []

                    for discord_account in roblox_data[1]:
                        username_str.append(f"{discord_account} ({discord_account.id})")

                    username_str = ", ".join(username_str)

                    if primary_account and roblox_username == primary_account.username:
                        primary_account_str = f"**{roblox_username}** {ARROW} {username_str}"
                    else:
                        parsed_accounts_str.append(f"**{roblox_username}** {ARROW} {username_str}")

                else:
                    parsed_accounts_str.append(f"**{roblox_username}**")

            parsed_accounts_str = "\n".join(parsed_accounts_str)


            embed = Embed(title="Linked Roblox Accounts")
            embed.add_field(name="Primary Account", value=primary_account_str)
            embed.add_field(name="Secondary Accounts", value=parsed_accounts_str or "No secondary account saved")
            embed.set_author(name=author, icon_url=author.avatar_url)

            await response.send(embed=embed, dm=True, strict_post=True)

    @staticmethod
    @Bloxlink.subcommand()
    async def unlink(CommandArgs):
        """unlink an account from Bloxlink"""

        author = CommandArgs.message.author
        prefix = CommandArgs.prefix
        response = CommandArgs.response

        guild = CommandArgs.message.guild
        guild_data = CommandArgs.guild_data

        try:
            _, accounts = await get_user("username", author=author, everything=False, basic_details=True)

            if accounts:
                parsed_accounts = await parse_accounts(accounts)
                parsed_accounts_str = ", ".join(parsed_accounts.keys())

                parsed_args = await CommandArgs.prompt([
                    {
                        "prompt": f"Please choose the account that you would like to unlink from: ```{parsed_accounts_str}```",
                        "name": "account",
                        "type": "choice",
                        "choices": parsed_accounts.keys(),
                        "formatting": False
                    },
                    {
                        "prompt": "We will now remove ``{account}`` from your account.\n"
                                  "**__WARNING:__** This will remove __all of your roles__ in server(s) you are linked "
                                  "as with this account.",
                        "footer": "Say **next** to continue.",
                        "type": "choice",
                        "choices": ["next"],
                        "name": "_",
                    }
                ], dm=True)

                username = parsed_args["account"]
                roblox_id = (parsed_accounts.get(username)).id

                try:
                    success = await unverify_member(author, roblox_id)
                except Blacklisted:
                    raise Error(f"You're not authorized to remove an account from Bloxlink.")

                if success:
                    await response.success(f"Successfully unlinked **{username}** from your account! Please note that it may take up to "
                                           f"{CACHE_CLEAR} minutes for the unlinking to reflect in every server you share with the bot due to "
                                            "Bloxlink using a cache for accounts.", dm=True, no_dm_post=True)

                    await post_event(guild, guild_data, "verification", f"{author.mention} has **unverified** from ``{username}``.", ORANGE_COLOR)
                else:
                    await response.send("Sorry, we failed to remove the account from you.")

        except UserNotVerified:
            raise Error(f"You're not linked to Bloxlink. Please use ``{prefix}verify add`` to add a new account.")
