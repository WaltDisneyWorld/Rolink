from resources.structures.Bloxlink import Bloxlink # pylint: disable=import-error
from resources.exceptions import Message, Error, CancelledPrompt, PermissionError # pylint: disable=import-error
from resources.constants import ARROW, OPTIONS, DEFAULTS, NICKNAME_TEMPLATES, ORANGE_COLOR, GOLD_COLOR, BROWN_COLOR # pylint: disable=import-error
from resources.secrets import TRELLO # pylint: disable=import-error
from discord import Embed, Object
from os import environ as env
from discord.errors import Forbidden
from aiotrello.exceptions import TrelloUnauthorized, TrelloNotFound, TrelloBadRequest


get_prefix, post_event = Bloxlink.get_module("utils", attrs=["get_prefix", "post_event"])
get_options = Bloxlink.get_module("trello", attrs=["get_options"])
parse_message = Bloxlink.get_module("commands", attrs=["parse_message"])
cache_set, cache_pop = Bloxlink.get_module("cache", attrs=["set", "pop"])
get_features = Bloxlink.get_module("premium", attrs=["get_features"])



RESET_CHOICES = ("everything", "binds")

options_keys = [o for o, o_d in OPTIONS.items() if not o_d[3]]
premium_option_keys = [o for o, o_d in OPTIONS.items() if o_d[3]]
options_combined = options_keys + premium_option_keys
options_strings = ", ".join([o for o, o_d in OPTIONS.items() if not o_d[3]])
premium_options_strings = ", ".join([o for o, o_d in OPTIONS.items() if o_d[3]])

@Bloxlink.command
class SettingsCommand(Bloxlink.Module):
    """change, view, or reset your Bloxlink settings"""

    def __init__(self):
        permission = Bloxlink.Permissions().build("BLOXLINK_MANAGER")
        permission.allow_bypass = True

        self.permissions = permission
        self.category = "Administration"
        self.aliases = ["config"]

    async def __main__(self, CommandArgs):
        choice = CommandArgs.string_args and CommandArgs.string_args[0].lower()

        if choice not in ("view", "change", "reset"):
            parsed_args = await CommandArgs.prompt([
                {
                    "prompt": "Would you like to **view** your settings, **change** them, or "
                              "**reset** all of your settings?\nIf you don't understand an option, "
                              "then say **help**.\nValid choices: (change/view/reset/help)",
                    "name": "choice",
                    "type": "choice",
                    "choices": ("change", "view", "reset", "help")
                }
            ])

            choice = parsed_args["choice"]

        if choice in ("change", "reset"):
            if not CommandArgs.has_permission:
                raise PermissionError("You do not have the required permissions to change server settings.")

        if choice == "view":
            await self.view(CommandArgs)
        elif choice == "change":
            await self.change(CommandArgs)
        elif choice == "reset":
            await self.reset(CommandArgs)
        elif choice == "help":
            await self.help(CommandArgs)

    @Bloxlink.subcommand()
    async def view(self, CommandArgs):
        """view your server settings"""

        guild = CommandArgs.message.guild
        guild_data = CommandArgs.guild_data
        response = CommandArgs.response
        trello_board = CommandArgs.trello_board
        prefix = CommandArgs.prefix

        embed = Embed(title="Bloxlink Settings")
        text_buffer = []
        options_trello_data = {}

        donator_profile, _ = await get_features(Object(id=guild.owner_id), guild=guild)

        if donator_profile.features.get("premium"):
            text_buffer.append("**This is a [Premium Server](https://www.patreon.com/join/bloxlink?)**\n")
            embed.colour = GOLD_COLOR

        if trello_board:
            options_trello_data, _ = await get_options(trello_board)
            guild_data.update(options_trello_data)

        for option_name, option_data in OPTIONS.items():
            value = None

            if option_data[0]:
                value = option_data[0](guild, guild_data) # pylint: disable=not-callable
            else:
                try:
                    value = str(guild_data.get(option_name, DEFAULTS.get(option_name, "False"))).replace("{prefix}", prefix)
                except KeyError:
                    value = str(guild_data.get(option_name, DEFAULTS.get(option_name, "False")))

            text_buffer.append(f"**{option_name}** {ARROW} {value}")

        embed.description = "\n".join(text_buffer)
        embed.set_footer(text="Powered by Bloxlink", icon_url=Bloxlink.user.avatar_url)
        embed.set_author(name=guild.name, icon_url=guild.icon_url)

        await response.send(embed=embed)


    @Bloxlink.subcommand()
    async def change(self, CommandArgs):
        """change your Bloxlink settings"""

        if not CommandArgs.has_permission:
            raise PermissionError("You do not have the required permissions to change server settings.")

        prefix = CommandArgs.prefix
        response = CommandArgs.response

        message = CommandArgs.message
        author = CommandArgs.message.author

        guild = CommandArgs.message.guild
        guild_data = CommandArgs.guild_data

        parsed_args = await CommandArgs.prompt([{
            "prompt": "What value would you like to change? Note that some settings you can't change "
                      "from this command due to the extra complexity, but I will tell you the "
                      f"appropriate command to use.\n\nOptions: ``{options_strings}``\n\nPremium-only options: ``{premium_options_strings}``",
            "name": "choice",
            "type": "choice",
            "formatting": False,
            "footer": f"Use ``{prefix}settings help`` to view a description of all choices.",
            "choices": options_combined
        }])

        choice = parsed_args["choice"]

        if choice == "trelloID":
            raise Message(f"You can link your Trello board from ``{prefix}setup``!", type="success")
        elif choice == "Linked Groups":
            raise Message(f"You can link your group from ``{prefix}bind``!", type="success")
        elif choice == "joinDM":
            message.content = f"{prefix}joindm"
            return await parse_message(message)
        elif choice == "groupShoutChannel":
            message.content = f"{prefix}shoutproxy"
            return await parse_message(message)
        elif choice == "whiteLabel":
            message.content = f"{prefix}whitelabel"
            return await parse_message(message)


        option_find = OPTIONS.get(choice)

        if option_find:
            if option_find[3]:
                profile, _ = await get_features(Object(id=guild.owner_id), guild=guild)

                if not profile.features.get("premium"):
                    raise Error("This option is premium-only! The server owner must have premium for it to be changed.\n"
                                f"Use ``{prefix}donate`` for more instructions on getting premium.")

            option_type = option_find[1]
            trello_board = CommandArgs.trello_board
            card = success_text = parsed_value = None
            desc = option_find[4].format(prefix=CommandArgs.prefix, templates=NICKNAME_TEMPLATES)

            if trello_board:
                options_trello_data, trello_binds_list = await get_options(trello_board, return_cards=True)
                options_trello_find = options_trello_data.get(choice)

                if options_trello_find:
                    card = options_trello_find[1]


            if option_type == "boolean":
                parsed_value = await CommandArgs.prompt([{
                    "prompt": f"Would you like to **enable** or **disable** ``{choice}``?\n\n"
                              f"**Option description:**\n{desc}",
                    "name": "choice",
                    "type": "choice",
                    "footer": "Say **clear** to set as the default value.",
                    "formatting": False,
                    "choices": ("enable", "disable", "clear")
                }])

                parsed_bool_choice = parsed_value["choice"]

                if parsed_bool_choice == "clear":
                    parsed_value = DEFAULTS.get(choice)
                else:
                    parsed_value = parsed_bool_choice == "enable"

                await self.r.table("guilds").insert({
                    "id": str(guild.id),
                    choice: parsed_value
                }, conflict="update").run()

                success_text = f"Successfully **{parsed_bool_choice}d** ``{choice}``!"

            elif option_type == "string":
                parsed_value = (await CommandArgs.prompt([{
                    "prompt": f"Please specify a new value for ``{choice}``.\n\n"
                              f"**Option description:**\n{desc}",
                    "name": "choice",
                    "type": "string",
                    "footer": "Say **clear** to set as the default value.",
                    "formatting": False,
                    "max": option_find[2]
                }]))["choice"]

                if parsed_value == "clear":
                    parsed_value = DEFAULTS.get(choice)

                await self.r.table("guilds").insert({
                    "id": str(guild.id),
                    choice: parsed_value
                }, conflict="update").run()

                success_text = f"Successfully saved your new {choice}!"

            elif option_type == "role":
                parsed_value = (await CommandArgs.prompt([{
                    "prompt": f"Please specify a role for ``{choice}``.\n\n"
                              f"**Option description:**\n{desc}",
                    "name": "role",
                    "type": "role",
                    "exceptions": ("clear",),
                    "footer": "Say **clear** to set as the default value.",
                    "formatting": False
                }]))["role"]

                if parsed_value == "clear":
                    parsed_value = DEFAULTS.get(choice)
                else:
                    parsed_value = str(parsed_value.id)

                await self.r.table("guilds").insert({
                    "id": str(guild.id),
                    choice: parsed_value
                }, conflict="update").run()

                success_text = f"Successfully saved your new ``{choice}``!"

            elif option_type == "number":
                parsed_value = (await CommandArgs.prompt([{
                    "prompt": f"Please specify a new integer for ``{choice}``.\n\n"
                              f"**Option description:**\n{desc}",
                    "name": "choice",
                    "type": "number",
                    "footer": "Say **clear** to set as the default value.",
                    "formatting": False,
                    "exceptions": ("clear",),
                    "max": option_find[2]
                }]))["choice"]

                if parsed_value == "clear":
                    parsed_value = DEFAULTS.get(choice)

                await self.r.table("guilds").insert({
                    "id": str(guild.id),
                    choice: int(parsed_value)
                }, conflict="update").run()

                success_text = f"Successfully saved your new ``{choice}``!"

            elif option_type == "choice":
                choices = ", ".join(option_find[2])
                parsed_value = (await CommandArgs.prompt([{
                    "prompt": f"Please pick a new value for ``{choice}``: ``{choices}``\n\n"
                              f"**Option description:**\n{desc}",
                    "name": "choice",
                    "type": "choice",
                    "footer": "Say **clear** to set as the default value.",
                    "formatting": False,
                    "exceptions": ["clear"],
                    "choices": option_find[2]
                }]))["choice"]

                if parsed_value == "clear":
                    parsed_value = DEFAULTS.get(choice)

                await self.r.table("guilds").insert({
                    "id": str(guild.id),
                    choice: parsed_value
                }, conflict="update").run()

                success_text = f"Successfully saved your new ``{choice}``!"
            else:
                raise Error("An unknown type was specified.")
        else:
            raise Error("An unknown option was specified.")

        if trello_board:
            try:
                if card:
                    if card.name == choice:
                        await card.edit(desc=str(parsed_value))
                    else:
                        await card.edit(name=f"{choice}:{parsed_value}")
                else:
                    trello_settings_list = await trello_board.get_list(lambda L: L.name == "Bloxlink Settings") \
                                           or await trello_board.create_list(name="Bloxlink Settings")

                    await trello_settings_list.create_card(name=choice, desc=str(parsed_value))

                if trello_binds_list:
                    await trello_binds_list.sync(card_limit=TRELLO["CARD_LIMIT"])

            except TrelloUnauthorized:
                await response.error("In order for me to edit your Trello settings, please add ``@bloxlink`` to your "
                                     "Trello board.")

            except (TrelloNotFound, TrelloBadRequest):
                pass

        await cache_set(choice, guild.id, parsed_value)

        await cache_pop("guild_data", guild.id)

        await post_event(guild, guild_data, "configuration", f"{author.mention} has **changed** the ``{choice}`` option.", BROWN_COLOR)

        raise Message(success_text, type="success")


    @Bloxlink.subcommand()
    async def reset(self, CommandArgs):
        """reset either ALL of your settings, or just your binds"""

        if not CommandArgs.has_permission:
            raise PermissionError("You do not have the required permissions to change server settings.")

        prefix = CommandArgs.prefix
        response = CommandArgs.response
        trello_board = CommandArgs.trello_board

        author = CommandArgs.message.author

        guild = CommandArgs.message.guild
        guild_data = CommandArgs.guild_data


        parsed_arg = (await CommandArgs.prompt([{
            "prompt": f"Which setting would you like to clear? Valid choices: ``{RESET_CHOICES}``",
            "name": "choice",
            "type": "choice",
            "formatting": False,
            "choices": RESET_CHOICES
        }]))["choice"]

        if parsed_arg == "everything":
            cont = (await CommandArgs.prompt([{
                "prompt": "**Warning!** This will clear **all of your settings** including binds, "
                          f"saved group information, etc. You'll need to run ``{prefix}setup`` "
                           "and set-up the bot again. Continue? ``Y/N``",
                "name": "continue",
                "choices": ("yes", "no"),
                "embed_title": "Warning!",
                "embed_color": ORANGE_COLOR,
                "type": "choice",
                "footer": "Say **yes** to clear all of your settings, or **no** to cancel."
            }]))["continue"]

            if cont == "no":
                raise CancelledPrompt

            await self.r.table("guilds").get(str(guild.id)).delete().run()

            if trello_board:
                trello_options, _ = await get_options(trello_board, return_cards=True)

                try:
                    if trello_options:
                        for option_name, option in trello_options.items():
                            await option[1].archive()

                    trello_binds_list = await trello_board.get_list(lambda l: l.name == "Bloxlink Binds")

                    if trello_binds_list:
                        for card in await trello_binds_list.get_cards(limit=TRELLO["CARD_LIMIT"]):
                            await card.archive()

                        trello_binds_list.parsed_bind_data = None

                except TrelloUnauthorized:
                    await response.error("In order for me to edit your Trello settings, please add ``@bloxlink`` to your "
                                         "Trello board.")
                except (TrelloNotFound, TrelloBadRequest):
                    pass
                else:
                    await trello_board.sync(card_limit=TRELLO["CARD_LIMIT"], list_limit=TRELLO["LIST_LIMIT"])


            await post_event(guild, guild_data, "configuration", f"{author.mention} has **deleted** all server information.", BROWN_COLOR)

            raise Message("Your server information was successfully cleared.", type="success")


        elif parsed_arg == "binds":
            # delete all binds from db and trello

            cont = (await CommandArgs.prompt([{
                "prompt": "**Warning!** This will clear **all of your binds**. You'll need to "
                         f"run ``{prefix}bind`` to set up your binds again. Continue? ``Y/N``",
                "name": "continue",
                "choices": ("yes", "no"),
                "type": "choice",
                "embed_title": "Warning!",
                "embed_color": ORANGE_COLOR,
                "formatting": False,
                "footer": "Say **yes** to clear all of your binds, or **no** to cancel."
            }]))["continue"]

            if cont == "no":
                raise CancelledPrompt

            guild_data = CommandArgs.guild_data
            role_binds = guild_data.get("roleBinds", {})

            if role_binds:
                role_ids = set()

                for group_id, group_data in role_binds.get("groups", {}).items():
                    for rank_id, rank_data in group_data.get("binds", {}).items():
                        for role_id in rank_data["roles"]:
                            role_ids.add(int(role_id))

                    for range_data in group_data.get("ranges", []):
                        if range_data["roles"]:
                            for role_id in range_data["roles"]:
                                role_ids.add(int(role_id))


                if role_ids:
                    delete_roles = (await CommandArgs.prompt([{
                        "prompt": "Would you like me to **delete these roles from your server as well?** If yes, "
                                  f"then this will delete **{len(role_ids)}** role(s). ``Y/N``",
                        "name": "delete_roles",
                        "choices": ("yes", "no"),
                        "type": "choice",
                        "embed_title": "Warning!",
                        "embed_color": ORANGE_COLOR,
                        "formatting": False,
                        "footer": "Say **yes** to delete these roles, or **no** to cancel."
                    }]))["delete_roles"]

                    if delete_roles == "yes":
                        for role_id in role_ids:
                            role = guild.get_role(role_id)

                            if role:
                                try:
                                    await role.delete(reason=f"{author} chose to delete bound roles through {prefix}settings")
                                except Forbidden:
                                    pass

                        await response.success("Your bound roles were deleted.")

            guild_data.pop("roleBinds", None)
            guild_data.pop("groupIDs", None)

            await self.r.table("guilds").insert(guild_data, conflict="replace").run()

            if trello_board:
                try:
                    trello_binds_list = await trello_board.get_list(lambda l: l.name == "Bloxlink Binds")

                    if trello_binds_list:
                        for card in await trello_binds_list.get_cards(limit=TRELLO["CARD_LIMIT"]):
                            await card.archive()

                        trello_binds_list.parsed_bind_data = None

                except TrelloUnauthorized:
                    await response.error("In order for me to edit your Trello settings, please add ``@bloxlink`` to your "
                                         "Trello board.")
                except (TrelloNotFound, TrelloBadRequest):
                    pass
                else:
                    await trello_board.sync(card_limit=TRELLO["CARD_LIMIT"], list_limit=TRELLO["LIST_LIMIT"])


            await post_event(guild, guild_data, "configuration", f"{author.mention} has **deleted** all binds.", BROWN_COLOR)

            raise Message("Successfully **cleared** all of your bound roles.", type="success")

    @Bloxlink.subcommand()
    async def help(self, CommandArgs):
        """provides a description of all changeable settings"""

        guild = CommandArgs.message.guild

        embed = Embed(title="Bloxlink Settings Help")
        embed.set_footer(text="Powered by Bloxlink", icon_url=Bloxlink.user.avatar_url)
        embed.set_author(name=guild.name, icon_url=guild.icon_url)

        for option_name, option_data in OPTIONS.items():
            desc = option_data[4].format(prefix=CommandArgs.prefix, templates=NICKNAME_TEMPLATES)
            embed.add_field(name=option_name, value=desc, inline=False)

        await CommandArgs.response.send(embed=embed)
