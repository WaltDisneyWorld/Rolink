from os import environ as env
from ast import literal_eval
from time import time


VERSION = "v3.0 ALPHA"

RELEASE = env.get("RELEASE", "LOCAL")
IS_DOCKER = env.get("LABEL")

WEBSOCKET_PORT = env.get("WEBSOCKET_PORT")
WEBSOCKET_SECRET = env.get("WEBSOCKET_SECRET")
CLUSTER_ID = int(env.get("CLUSTER_ID", 0))
LABEL = env.get("LABEL", "master").lower()
SHARD_RANGE = literal_eval(env.get("SHARD_RANGE", "(0,)"))

STARTED = time()

RED_COLOR = 0xE74C3C
INVISIBLE_COLOR = 0x36393E
ORANGE_COLOR = 0xCE8037

NICKNAME_TEMPLATES = (
    "{roblox-name} \u2192 changes to their Roblox username\n"
    "{roblox-id} \u2192 changes to their Roblox user ID\n"
    "{roblox-age} \u2192 changes to their Roblox user age in days\n"
    "{roblox-join-date} \u2192 changes to their Roblox join date\n"
    "{group-rank} \u2192 changes to their group rank\n"
    "{group-rank-ID} \u2192 changes to their group rank in group with ID\n"
    "{discord-name} \u2192 changes to their Discord display name\n"
    "{discord-nick} \u2192 changes to their Discord nickname\n"
    "{server-name} \u2192 changes to the server name\n"
    "\n"
    "{disable-nicknaming} \u2192 overrides all other options and returns a blank nickname. Note that this ONLY APPLIES TO NICKNAMES."
)

UNVERIFIED_TEMPLATES = (
    "{discord-name} \u2192 changes to their Discord display name\n"
    "{discord-nick} \u2192 changes to their Discord nickname\n"
    "{server-name} \u2192 changes to the server name"
)

OPTIONS = {                # fn,  type, max length, desc
    "prefix":              (None, "string", 10,    "The prefix is used before commands to activate them"),   #
    "verifiedRoleName":    (None, "string", 20,    "The Verified role is given to people who are linked on Bloxlink. You can change the name of the role here."),
    "verifiedRoleEnabled": (None, "boolean", None, "The Verified role is given to people who are linked on Bloxlink. Enable/disable it here."),      #
    "Linked Groups":       (None,  None, None,     "Bind groups to your server so group members get specific roles."),          #
    "allowOldRoles":       (None, "boolean", None, "Bloxlink will NOT remove roles if this is enabled."),      #
    "autoRoles":           (None, "boolean", None, "Bloxlink will give all matching/corresponding roles to people who join the server. Set eligible roles with ``{prefix}bind``. Note that this being enabled will override 'autoVerification'."),      #
    "autoVerification":    (None, "boolean", None, "Bloxlink will give the Verified role to people who join the server and are linked to Bloxlink.\nNote that 'autoRoles' being enabled overrides this setting."),      #
    "dynamicRoles":        (None, "boolean", None, "Bloxlink will make missing group roles from your Linked Groups as people need them."),      #
    "welcomeMessage":      (None, "string", 1500,  "The welcome message is used on ``{prefix}verify`` responses. Note that you can use these templates: ```{templates}```"),
    "joinDM":              (None, None, None,      "Customize the join DM messages of people who join the server."),
    "persistRoles":        (None, "boolean", None, "Update members' roles/nickname as they type."),
    "groupLock":           (None, "boolean", None, "Lock your server to members of a group."),
    "allowReVerify":       (None, "boolean", None, "If this is enabled: members can change their Roblox account as many times as they want to in your server; otherwise, only allow 1 account."),
    "trelloID":            (None,  None, None,     "Link a Trello board that can change Bloxlink settings!")           #
}

DEFAULTS = {
    "prefix": "!",
    "Linked Groups": "view using ``@Bloxlink viewbinds``",
    "verifiedRoleName": "Verified",
    "verifiedRoleEnabled": True,
    "autoRoles": True,
    "autoVerification": True,
    "dynamicRoles": True,
    "trelloID": "No Trello Board",
    "allowReVerify": True,
    "welcomeMessage": "Welcome to **{server-name}**, {roblox-name}!"

}

ARROW = "\u2192"

MAGIC_ROLES = ["Bloxlink Admin", "Bloxlink Bypass", "Bloxlink Updater"]

OWNER = 84117866944663552

HELP_DESCRIPTION = "**Welcome to Bloxlink!**\n\n" \
	               "**Support Server:** https://blox.link/support\n" \
	               "**Website:** https://blox.link/\n" \
	               "**Invite:** https://blox.link/invite\n" \
	               "**Documentation:** https://github.com/bloxlink/docs\n\n" \
	               "Please use ``{prefix}setup`` to set-up your server."

WELCOME_MESSAGE = "Welcome to **{server-name}**, {roblox-name}!"
