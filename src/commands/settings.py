from resources.structures.Bloxlink import Bloxlink # pylint: disable=import-error
from resources.exceptions import Message, Error, CancelledPrompt # pylint: disable=import-error
from resources.constants import ARROW, OPTIONS, DEFAULTS # pylint: disable=import-error
from config import TRELLO # pylint: disable=no-name-in-module
from discord import Embed
from discord.errors import Forbidden
from aiotrello.exceptions import TrelloUnauthorized, TrelloNotFound, TrelloBadRequest

get_prefix = Bloxlink.get_module("utils", attrs=["get_prefix"])
get_options = Bloxlink.get_module("trello", attrs=["get_options"])



RESET_CHOICES = ("everything", "binds")

options_keys = tuple(OPTIONS.keys())

@Bloxlink.command
class SettingsCommand(Bloxlink.Module):
    """change, view, or reset your Bloxlink settings"""

    def __init__(self):
        permission = Bloxlink.Permissions().build("BLOXLINK_MANAGER")
        permission.allow_bypass = True

        self.permissions = permission

    async def __main__(self, CommandArgs):
        choice = CommandArgs.string_args and CommandArgs.string_args[0].lower()

        if choice not in ("view", "change", "reset"):
            parsed_args = await CommandArgs.prompt([
                {
                    "prompt": "Would you like to **view** your settings, **change** them, or "
                              "**reset** all of your settings?\nValid choices: (change/view/reset)",
                    "name": "choice",
                    "type": "choice",
                    "choices": ("change", "view", "reset")
                }
            ])

            choice = parsed_args["choice"]

        if choice in ("change", "reset"):
            if not CommandArgs.has_permission:
                raise PermissionError("You do not meet the required permissions to change server settings.")

        if choice == "view":
            await self.view(CommandArgs)
        elif choice == "change":
            await self.change(CommandArgs)
        elif choice == "reset":
            await self.reset(CommandArgs)

    @Bloxlink.subcommand()
    async def view(self, CommandArgs):
        guild = CommandArgs.message.guild
        guild_data = CommandArgs.guild_data
        response = CommandArgs.response
        trello_board = CommandArgs.trello_board

        embed = Embed(title="Bloxlink Settings")
        text_buffer = []
        options_trello_data = {}

        if trello_board:
            options_trello_data, _ = await get_options(trello_board)
            guild_data.update(options_trello_data)

        for option_name, option_data in OPTIONS.items():
            value = None

            if option_data[0]:
                value = option_data[0](guild_data) # pylint: disable=not-callable
            else:
                value = guild_data.get(option_name, DEFAULTS.get(option_name, "False"))

            text_buffer.append(f"**{option_name}** {ARROW} {value}")

        embed.description = "\n".join(text_buffer)
        embed.set_footer(text="Powered by Bloxlink", icon_url=Bloxlink.user.avatar_url)
        embed.set_author(name=guild.name, icon_url=guild.icon_url)

        await response.send(embed=embed)


    @Bloxlink.subcommand()
    async def change(self, CommandArgs):
        if not CommandArgs.has_permission:
            raise PermissionError("You do not meet the required permissions to change server settings.")

        prefix = CommandArgs.prefix
        guild = CommandArgs.message.guild
        response = CommandArgs.response

        parsed_args = await CommandArgs.prompt([{
            "prompt": "What value would you like to change? Note that some settings you can't change "
                      "from this command due to the extra complexity, but I will tell you the "
                      f"appropriate command to use.\n\nOptions: ``{options_keys}``",
            "name": "choice",
            "type": "choice",
            "formatting": False,
            "choices": options_keys
        }])

        choice = parsed_args["choice"]

        if choice == "trelloID":
            raise Message(f"You can link your Trello board from ``{prefix}setup``!", type="success")
        elif choice == "Linked Groups":
            raise Message(f"You can link your group from ``{prefix}bind``!", type="success")

        option_find = OPTIONS.get(choice)

        if option_find:
            option_type = option_find[1]
            trello_board = CommandArgs.trello_board
            card = success_text = parsed_value = None

            if trello_board:
                options_trello_data, trello_binds_list = await get_options(trello_board, return_cards=True)
                options_trello_find = options_trello_data.get(choice.lower())

                if options_trello_find:
                    card = options_trello_find[1]


            if option_type == "boolean":
                parsed_value = await CommandArgs.prompt([{
                    "prompt": f"Would you like to **enable** or **disable** ``{choice}``?",
                    "name": "choice",
                    "type": "choice",
                    "formatting": False,
                    "choices": ("enable", "disable")
                }])

                parsed_bool_choice = parsed_value["choice"]
                parsed_value = parsed_bool_choice == "enable"

                await self.r.table("guilds").insert({
                    "id": str(guild.id),
                    choice: parsed_value
                }, conflict="update").run()

                success_text = f"Successfully **{parsed_bool_choice}d** ``{choice}``!"

            elif option_type == "string":
                parsed_value = (await CommandArgs.prompt([{
                    "prompt": f"Please specify a new value for ``{choice}``.",
                    "name": "choice",
                    "type": "string",
                    "formatting": False,
                    "max": option_find[2]
                }]))["choice"]

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
                        await card.edit(desc=parsed_value)
                    else:
                        await card.edit(name=f"{choice}:{parsed_value}")
                else:
                    trello_settings_list = await trello_board.get_list(lambda L: L.name == "Bloxlink Settings") \
                                           or await trello_board.create_list(name="Bloxlink Settings")

                    await trello_settings_list.create_card(name=choice, desc=parsed_value)

                await trello_binds_list.sync(card_limit=TRELLO["GLOBAL_CARD_LIMIT"])

            except TrelloUnauthorized:
                await response.error("In order for me to edit your Trello settings, please add ``@bloxlink`` to your "
                                     "Trello board.")

            except (TrelloNotFound, TrelloBadRequest):
                pass


        raise Message(success_text, type="success")


    @Bloxlink.subcommand()
    async def reset(self, CommandArgs):
        if not CommandArgs.has_permission:
            raise PermissionError("You do not meet the required permissions to change server settings.")

        prefix = CommandArgs.prefix
        guild = CommandArgs.message.guild
        trello_board = CommandArgs.trello_board
        response = CommandArgs.response

        parsed_arg = (await CommandArgs.prompt([{
            "prompt": f"Which setting would you like to clear? Valid choices: ``{RESET_CHOICES}``",
            "name": "choice",
            "type": "choice",
            "formatting": False,
            "choices": RESET_CHOICES
        }]))["choice"]

        if parsed_arg == "everything":
            # warn that this will delete everything
            # including all trello cards in Bloxlink Settings
            cont = (await CommandArgs.prompt([{
                "prompt": "Warning! This will clear **all of your settings** including binds, "
                          f"saved group information, etc. You'll need to run ``{prefix}setup`` "
                           "and set-up the bot again. Continue? ``y/n``",
                "name": "continue",
                "choices": ("yes", "no"),
                "type": "choice"
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
                        for card in await trello_binds_list.get_cards(limit=TRELLO["GLOBAL_CARD_LIMIT"]):
                            await card.archive()

                        trello_binds_list.parsed_bind_data = None

                except TrelloUnauthorized:
                    await response.error("In order for me to edit your Trello settings, please add ``@bloxlink`` to your "
                                         "Trello board.")
                except (TrelloNotFound, TrelloBadRequest):
                    pass
                else:
                    await trello_board.sync(card_limit=TRELLO["GLOBAL_CARD_LIMIT"])

            raise Message("Your server information was successfully cleared.", type="success")


        elif parsed_arg == "binds":
            # delete all binds from db and trello

            cont = (await CommandArgs.prompt([{
                "prompt": "Warning! This will clear **all of your binds**. You'll need to "
                         f"run ``{prefix}bind`` to set up your binds again. Continue? ``y/n``",
                "name": "continue",
                "choices": ("yes", "no"),
                "type": "choice",
                "formatting": False
            }]))["continue"]

            if cont == "no":
                raise CancelledPrompt

            guild_data = CommandArgs.guild_data
            role_binds = guild_data.get("roleBinds", {})

            if role_binds:
                role_ids = set()

                for group_id, group_data in role_binds["groups"].items():
                    for rank_id, rank_data in group_data.get("binds", {}).items():
                        for role_id in rank_data["roles"]:
                            role_ids.add(int(role_id))

                    for range_data in group_data.get("ranges", []):
                        if range_data["roles"]:
                            for role_id in range_data["roles"]:
                                role_ids.add(int(role_id))


                if role_ids:
                    delete_roles = (await CommandArgs.prompt([{
                        "prompt": "Would you like me to delete these roles from your server as well? If yes, "
                                  f"then this will delete **{len(role_ids)}** role(s). ``y/n``",
                        "name": "delete_roles",
                        "choices": ("yes", "no"),
                        "type": "choice",
                        "formatting": False
                    }]))["delete_roles"]

                    if delete_roles == "yes":
                        for role_id in role_ids:
                            role = guild.get_role(role_id)

                            if role:
                                try:
                                    await role.delete()
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
                        for card in await trello_binds_list.get_cards(limit=TRELLO["GLOBAL_CARD_LIMIT"]):
                            await card.archive()

                        trello_binds_list.parsed_bind_data = None

                except TrelloUnauthorized:
                    await response.error("In order for me to edit your Trello settings, please add ``@bloxlink`` to your "
                                         "Trello board.")
                except (TrelloNotFound, TrelloBadRequest):
                    pass
                else:
                    await trello_board.sync(card_limit=TRELLO["GLOBAL_CARD_LIMIT"])

            raise Message("Successfully cleared all of your bound roles.", type="success")
