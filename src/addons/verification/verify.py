from resources.structures.Bloxlink import Bloxlink # pylint: disable=import-error
from discord import Embed, Object
from resources.exceptions import Message, UserNotVerified, Error, RobloxNotFound, BloxlinkBypass, Blacklisted, PermissionError # pylint: disable=import-error
from resources.constants import (NICKNAME_TEMPLATES, GREEN_COLOR, BROWN_COLOR, ARROW, VERIFY_URL, # pylint: disable=import-error
                                ACCOUNT_SETTINGS_URL, TRELLO)
from aiotrello.exceptions import TrelloNotFound, TrelloUnauthorized, TrelloBadRequest

verify_as, get_user, get_nickname, get_roblox_id, parse_accounts, unverify_member, format_update_embed, guild_obligations = Bloxlink.get_module("roblox", attrs=["verify_as", "get_user", "get_nickname", "get_roblox_id", "parse_accounts", "unverify_member", "format_update_embed", "guild_obligations"])
get_options = Bloxlink.get_module("trello", attrs="get_options")
post_event = Bloxlink.get_module("utils", attrs=["post_event"])



class VerifyCommand(Bloxlink.Module):
    """link your Roblox account to your Discord account and get your server roles"""

    def __init__(self):
        self.examples = ["add", "unlink", "view", "blox_link"]
        self.category = "Account"
        self.cooldown = 5
        self.aliases = ["getrole", "getroles"]
        self.dm_allowed = True

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

        if not guild:
            return await self.add(CommandArgs)

        if CommandArgs.flags.get("add") or CommandArgs.flags.get("verify") or CommandArgs.flags.get("force"):
            await CommandArgs.response.error(f"``{CommandArgs.prefix}verify --force`` is deprecated and will be removed in a future version of Bloxlink. "
                                             f"Please use ``{prefix}verify add`` instead.")

            return await self.add(CommandArgs)

        if CommandArgs.real_command_name in ("getrole", "getroles"):
            CommandArgs.string_args = []

        trello_options = {}

        if trello_board:
            trello_options, _ = await get_options(trello_board)
            guild_data.update(trello_options)

        try:
            old_nickname = author.display_name

            added, removed, nickname, errors, roblox_user = await guild_obligations(
                CommandArgs.message.author,
                guild                = guild,
                guild_data           = guild_data,
                roles                = True,
                nickname             = True,
                trello_board         = CommandArgs.trello_board,
                given_trello_options = True,
                cache                = False,
                response             = response,
                dm                   = False,
                exceptions           = ("BloxlinkBypass", "Blacklisted", "UserNotVerified", "PermissionError")
            )

        except BloxlinkBypass:
            raise Message("Since you have the ``Bloxlink Bypass`` role, I was unable to update your roles/nickname.", type="info")

        except Blacklisted as b:
            if str(b):
                raise Error(f"{author.mention} has an active restriction for: ``{b}``")
            else:
                raise Error(f"{author.mention} has an active restriction from Bloxlink.")

        except UserNotVerified:
            await self.add(CommandArgs)

        except PermissionError as e:
            raise Error(e)

        else:
            welcome_message, embed = await format_update_embed(roblox_user, author, added=added, removed=removed, errors=errors, nickname=nickname if old_nickname != author.display_name else None, prefix=prefix, guild_data=guild_data)

            if embed:
                await post_event(guild, guild_data, "verification", f"{author.mention} ({author.id}) has **verified** as ``{roblox_user.username}``.", GREEN_COLOR)
            else:
                embed = Embed(description="This user is all up-to-date; no changes were made.")

            await response.send(content=welcome_message, embed=embed)


    @Bloxlink.subcommand()
    async def add(self, CommandArgs):
        """link a new account to Bloxlink"""

        author = CommandArgs.message.author

        if CommandArgs.message.guild:
            guild_data = CommandArgs.guild_data

            if not guild_data.get("hasBot"):
                guild_data["hasBot"] = True

                await self.r.table("guilds").insert(guild_data, conflict="update").run()

            response_text = f"{author.mention}, to verify with Bloxlink, please visit our website at " \
                            f"<{VERIFY_URL}>. It won't take long!\nStuck? See this video: <https://www.youtube.com/watch?v=hq496NmQ9GU>"
        else:
            response_text = "To verify with Bloxlink, please visit our website at " \
                            f"<{VERIFY_URL}>. It won't take long!\nStuck? See this video: <https://www.youtube.com/watch?v=hq496NmQ9GU>"

        await CommandArgs.response.send(response_text)


    @Bloxlink.subcommand(permissions=Bloxlink.Permissions().build("BLOXLINK_MANAGER"))
    async def customize(self, CommandArgs):
        """customize the behavior of !verify"""

        # TODO: able to set: "forced groups"

        prefix = CommandArgs.prefix
        response = CommandArgs.response

        author = CommandArgs.message.author

        guild = CommandArgs.message.guild
        guild_data = CommandArgs.guild_data

        if not guild:
            return await response.send("This sub-command can only be used in a server!")

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

        await post_event(guild, guild_data, "configuration", f"{author.mention} ({author.id}) has **changed** the ``{choice}``.", BROWN_COLOR)

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

        if CommandArgs.message.guild:
            await CommandArgs.response.reply(f"to manage your accounts, please visit our website: <{ACCOUNT_SETTINGS_URL}>")
        else:
            await CommandArgs.response.send(f"To manage your accounts, please visit our website: <{ACCOUNT_SETTINGS_URL}>")
