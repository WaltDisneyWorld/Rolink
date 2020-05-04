from os import environ as env
from ast import literal_eval
from time import time
from re import search

VERSION = "v3.0 ALPHA"

RELEASE = env.get("RELEASE", "LOCAL")
IS_DOCKER = bool(env.get("RELEASE"))


SHARDS_PER_CLUSTER = int(env.get("SHARDS_PER_CLUSTER", "1"))

CLUSTER_ID = env.get("CLUSTER_ID") or search(r".+\-(\d)", env.get("HOSTNAME", "canary-0"))
CLUSTER_ID = (CLUSTER_ID and (isinstance(CLUSTER_ID, str) and CLUSTER_ID.isdigit() and int(CLUSTER_ID)) or int(CLUSTER_ID.group(1))) or 0

SHARD_COUNT = int(env.get("SHARD_COUNT", "1"))

SHARD_RANGE = []

_to_add = 0
for _ in range(SHARDS_PER_CLUSTER):
  shard = (CLUSTER_ID * SHARDS_PER_CLUSTER) + _to_add

  if shard + 1 > SHARD_COUNT:
      break

  SHARD_RANGE.append(shard)
  _to_add += 1


STARTED = time()

RED_COLOR       = 0xE74C3C
INVISIBLE_COLOR = 0x36393E
ORANGE_COLOR    = 0xCE8037
GOLD_COLOR      = 0xFDC333

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
    "prefix":              (None, "string", 10,    "The prefix is used before commands to activate them"), #
    "verifiedRoleName":    (None, "string", 20,    "The Verified role is given to people who are linked on Bloxlink. You can change the name of the role here."), #
    "verifiedRoleEnabled": (None, "boolean", None, "The Verified role is given to people who are linked on Bloxlink. Enable/disable it here."), #
    "Linked Groups":       (None,  None, None,     "Bind groups to your server so group members get specific roles."), #
    "allowOldRoles":       (None, "boolean", None, "Bloxlink will NOT remove roles if this is enabled."), #
    "autoRoles":           (None, "boolean", None, "Bloxlink will give all matching/corresponding roles to people who join the server. Set eligible roles with ``{prefix}bind``. Note that this being enabled will override 'autoVerification'."), #
    "autoVerification":    (None, "boolean", None, "Bloxlink will give the Verified role to people who join the server and are linked to Bloxlink.\nNote that 'autoRoles' being enabled overrides this setting."), #
    "dynamicRoles":        (None, "boolean", None, "Bloxlink will make missing group roles from your Linked Groups as people need them."), #
    "welcomeMessage":      (None, "string", 1500,  "The welcome message is used on ``{prefix}verify`` responses. Note that you can use these templates: ```{templates}```"), #
    "joinDM":              (None, None, None,      "Customize the join DM messages of people who join the server."), #
    "persistRoles":        (None, "boolean", None, "Update members' roles/nickname as they type."),
    "allowReVerify":       (None, "boolean", None, "If this is enabled: members can change their Roblox account as many times as they want to in your server; otherwise, only allow 1 account."), #
    "trelloID":            (None,  None, None,     "Link a Trello board that can change Bloxlink settings!"), #
    "nicknameTemplate":    (None,  "string", 100, "Set the universal nickname template. Note that ``{prefix}bind`` nicknames will override this."),
    "unverifiedRoleName":  (None,  "string", 100, "Set the 'Unverified' role name -- the role that Unverified users get."),
}

DEFAULTS = {
    "prefix": "{prefix}",
    "Linked Groups": "view using ``@Bloxlink viewbinds``",
    "verifiedRoleName": "Verified",
    "verifiedRoleEnabled": True,
    "allowOldRoles": False,
    "autoRoles": True,
    "autoVerification": True,
    "dynamicRoles": True,
    "trelloID": "No Trello Board",
    "allowReVerify": True,
    "welcomeMessage": "Welcome to **{server-name}**, {roblox-name}!",
    "nicknameTemplate": "{roblox-name}",
    "unverifiedRoleName": "Unverified"

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
