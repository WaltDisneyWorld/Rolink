from resources.structures.Bloxlink import Bloxlink  # pylint: disable=import-error
from resources.exceptions import Error, Message, UserNotVerified  # pylint: disable=import-error
from resources.constants import WELCOME_MESSAGE  # pylint: disable=import-error
from discord.errors import Forbidden, NotFound, HTTPException


get_options, get_board = Bloxlink.get_module("trello", attrs=["get_options", "get_board"])
get_user, verify_as, parse_accounts, update_member, get_nickname, verify_member = Bloxlink.get_module("roblox", attrs=["get_user", "verify_as", "parse_accounts", "update_member", "get_nickname", "verify_member"])



@Bloxlink.command
class SwitchUserCommand(Bloxlink.Module):
    """change your linked Roblox account in a server"""

    def __init__(self):
        pass


    @staticmethod
    async def validate_server(message, content):
        content = content.lower()

        if content in ("skip", "next"):
            return message.guild

        if not content.isdigit():
            return None, "A server ID must be a number."

        try:
            guild = await Bloxlink.fetch_guild(int(content))
        except Forbidden:
            return None, "I'm not a member of this server."
        except HTTPException:
            return None, "This is an invalid server ID."
        else:
            return guild


    async def __main__(self, CommandArgs):
        author = CommandArgs.message.author
        response = CommandArgs.response
        prefix = CommandArgs.prefix

        author_data = await self.r.table("users").get(str(author.id)).run() or {"id": str(author.id)}

        try:
            primary_account, accounts = await get_user("username", author=author, everything=False, basic_details=True)

            if accounts:
                parsed_accounts = await parse_accounts(accounts)
                parsed_accounts_str = ", ".join(parsed_accounts.keys())

                parsed_args = await CommandArgs.prompt([
                    {
                        "prompt": "This command will allow you to switch into an account you verified as in the past.\n"
                                  f"If you would like to link __a new account__, then please use ``{prefix}verify add``.\n\n"
                                  "**__WARNING:__** This will remove __all of your roles__ in the server and give you "
                                  "new roles depending on the server configuration.",
                        "footer": "Say **next** to continue.",
                        "type": "choice",
                        "choices": ["next"],
                        "name": "_",
                        "formatting": False
                    },
                    {
                        "prompt": "Are you trying to change your account for _this_ server? If so, simply say ``next``.\nIf not, please provide "
                                  "the __Server ID__ of the server to switch as. Please see this article to find the Server ID: "
                                  "[click here](https://support.discordapp.com/hc/en-us/articles/206346498-Where-can-I-find-my-User-Server-Message-ID->).",
                        "name": "guild",
                        "validation": self.validate_server,
                    },
                    {
                        "prompt": "We'll switch your account for the server **{guild.name}**.\n"
                                  "Please select an account to switch into:```" + parsed_accounts_str + "```",
                        "name": "account",
                        "type": "choice",
                        "choices": parsed_accounts.keys()
                    },
                    {
                        "prompt": "Would you like to make this your __primary__ account? Please say **yes** or **no**.",
                        "name": "primary",
                        "type": "choice",
                        "choices": ("yes", "no")
                    }
                ])

                guild = parsed_args["guild"]
                username = parsed_args["account"]

                guild_data = await self.r.table("guilds").get(str(guild.id)).run() or {}

                trello_board = await get_board(guild_data=guild_data, guild=guild)

                if trello_board:
                    options_trello, _ = await get_options(trello_board)
                    guild_data.update(options_trello)

                allow_reverify = guild_data.get("allowReVerify", True)

                try:
                    member = await guild.fetch_member(author.id)
                except (Forbidden, NotFound):
                    roblox_id = (parsed_accounts.get(username)).id

                    await verify_member(author, roblox_id, guild=guild, author_data=author_data, allow_reverify=allow_reverify, primary_account=parsed_args["primary"] == "yes")
                    raise Message("You're not a member of the provided server, so I was only able to update your account internally.\nPlease allow "
                                  "up to 10 minutes for the internal cache to clear.", type="success")

                try:
                    username = await verify_as(
                        member,
                        guild,
                        response     = response,
                        primary      = parsed_args["primary"] == "yes",
                        username     = username,
                        trello_board = trello_board)

                except Message as e:
                    if e.type == "error":
                        await response.error(e)
                    else:
                        await response.send(e)
                except Error as e:
                    await response.error(e)
                else:
                    for role in list(member.roles):
                        if role != guild.default_role:
                            try:
                                await member.remove_roles(role, reason="Switched User")
                            except Forbidden:
                                pass

                    added, removed, nickname, errors, roblox_user = await update_member(
                        member,
                        guild      = guild,
                        roles      = True,
                        nickname   = True,
                        author_data  = await self.r.table("users").get(str(author.id)).run())


                    welcome_message = guild_data.get("welcomeMessage") or WELCOME_MESSAGE

                    welcome_message = await get_nickname(author, welcome_message, guild_data=guild_data, roblox_user=roblox_user, is_nickname=False)

                    await CommandArgs.response.send(welcome_message)

            else:
                raise Message(f"You only have one account linked! Please use ``{prefix}verify add`` to add another.", type="silly")


        except UserNotVerified:
            raise Error("You're not linked to Bloxlink. Please use ``{prefix}verify add``.")
