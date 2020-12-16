from os import environ as env
from time import time
from re import search
from discord import Game
from discord.utils import find

VERSION = "v3.14.3"

RELEASE = env.get("RELEASE", "LOCAL")
IS_DOCKER = bool(env.get("RELEASE"))

TOPGG_API = "https://top.gg/api"
DBL_API = "https://discordbotlist.com/api/v1"

SHARDS_PER_CLUSTER = int(env.get("SHARDS_PER_CLUSTER", "1"))

CLUSTER_ID = env.get("CLUSTER_ID") or search(r".+\-(\d+)", env.get("HOSTNAME", "bloxlink-0"))
CLUSTER_ID = (CLUSTER_ID and ((isinstance(CLUSTER_ID, str) and CLUSTER_ID.isdigit() and int(CLUSTER_ID)) or int(CLUSTER_ID.group(1)))) or 0

SHARD_COUNT = int(env.get("SHARD_COUNT", "1"))

SHARD_RANGE = []

_to_add = 0
for _ in range(SHARDS_PER_CLUSTER):
  shard = (CLUSTER_ID * SHARDS_PER_CLUSTER) + _to_add

  if shard + 1 > SHARD_COUNT:
      break

  SHARD_RANGE.append(shard)
  _to_add += 1

SELF_HOST = True # changes bot behavior, such as using the Bloxlink API for requests

STARTED = time()

RED_COLOR       = 0xdb2323
INVISIBLE_COLOR = 0x36393E
ORANGE_COLOR    = 0xCE8037
GOLD_COLOR      = 0xFDC333
CYAN_COLOR      = 0x4DD3CC
PURPLE_COLOR    = 0xa830c5
GREEN_COLOR     = 0x0ec37e
BROWN_COLOR     = 0xa2734a
BLURPLE_COLOR   = 0x4a58a2
YELLOW_COLOR    = 0xf1c40f
PINK_COLOR      = 0xf47fff

DEV_COLOR               = 0x4DD3CC
STAFF_COLOR             = 0x3ca770
COMMUNITY_MANAGER_COLOR = 0xc4306f
VIP_MEMBER_COLOR        = 0x3271c2
PARTNERS_COLOR          = 0xda43d1

PARTNERED_SERVER        = 0x4f91a0

if RELEASE == "PRO":
    EMBED_COLOR = YELLOW_COLOR
elif RELEASE == "MAIN":
    EMBED_COLOR = RED_COLOR
elif RELEASE == "CANARY":
    EMBED_COLOR = ORANGE_COLOR
elif RELEASE == "LOCAL":
    EMBED_COLOR = PURPLE_COLOR
"""
if RELEASE == "CANARY":
    VERIFY_URL = "https://canary.blox.link/verify/"
    ACCOUNT_SETTINGS_URL = "https://canary.blox.link/account/"
else:
"""

VERIFY_URL = "https://blox.link/verify/"
ACCOUNT_SETTINGS_URL = "https://blox.link/account/"

NICKNAME_TEMPLATES = (
    "{roblox-name} \u2192 changes to their Roblox username\n"
    "{roblox-id} \u2192 changes to their Roblox user ID\n"
    "{roblox-age} \u2192 changes to their Roblox user age in days\n"
    "{roblox-join-date} \u2192 changes to their Roblox join date\n"
    "{group-rank} \u2192 changes to their group rank\n"
    "{group-rank-ID} \u2192 changes to their group rank in group with ID\n"
    "{discord-name} \u2192 changes to their Discord display name; works on unverified users\n"
    "{discord-nick} \u2192 changes to their Discord nickname; works on unverified users\n"
    "{server-name} \u2192 changes to the server name; works on unverified users\n"
    "{prefix} \u2192 changes to the server prefix; works on unverified users\n"
    "{clan-tag} \u2192 replaceable text which the user can set\n"
    "\n"
    "{disable-nicknaming} \u2192 overrides all other options and returns a blank nickname. Note that this ONLY APPLIES TO NICKNAMES."
)

UNVERIFIED_TEMPLATES = (
    "{discord-name} \u2192 changes to their Discord display name\n"
    "{discord-nick} \u2192 changes to their Discord nickname\n"
    "{server-name} \u2192 changes to the server name"
)

ESCAPED_NICKNAME_TEMPLATES = NICKNAME_TEMPLATES.replace("{", "{{").replace("}", "}}")

OPTIONS = {                # fn,  type, max length or choices, premium only, desc
    "prefix":                (lambda g, gd: RELEASE == "PRO" and gd.get("proPrefix") or gd.get("prefix"), "string", 10,    False, "The prefix is used before commands to activate them"),
    "verifiedRoleName":      (None, "string", 20,    False, "The Verified role is given to people who are linked on Bloxlink. You can change the name of the role here."),
    "verifiedRoleEnabled":   (None, "boolean", None, False, "The Verified role is given to people who are linked on Bloxlink. Enable/disable it here."),
    "unverifiedRoleEnabled": (None, "boolean", None, False, "The Unverified role is given to people who aren't linked on Bloxlink. Enable/disable it here."),
    "Linked Groups":         (None,  None, None,     False, "Bind groups to your server so group members get specific roles."),
    "allowOldRoles":         (None, "boolean", None, False, "Bloxlink will NOT remove roles if this is enabled."),
    "autoRoles":             (None, "boolean", None, False, "Bloxlink will give all matching/corresponding roles to people who join the server. Set eligible roles with ``{prefix}bind``. Note that this being enabled will override 'autoVerification'."),
    "autoVerification":      (None, "boolean", None, False, "Bloxlink will give the Verified role to people who join the server and are linked to Bloxlink.\nNote that 'autoRoles' being enabled overrides this setting."),
    #"dmVerifications":       (None, "boolean", None, False, "Set whether verifications default to DMs."),
    "dynamicRoles":          (None, "boolean", None, False, "Bloxlink will make missing group roles from your Linked Groups as people need them."),
    "welcomeMessage":        (None, "string", 1500,  False, "The welcome message is used on ``{prefix}verify`` responses. Note that you can use these templates: ```{templates}```"),
    "joinDM":                (lambda g, gd: bool(gd.get("verifiedDM", True)) or bool(gd.get("unverifiedDM")), None, None, False, "Customize the join DM messages of people who join the server."),
    "persistRoles":          (None, "boolean", None, True,  "Update members' roles/nickname as they type."),
    "allowReVerify":         (None, "boolean", None, True,  "If this is enabled: members can change their Roblox account as many times as they want in your server; otherwise, only allow 1 account change."),
    "trelloID":              (None,  None, None,     False, "Link a Trello board that can change Bloxlink settings!"),
    "nicknameTemplate":      (None,  "string", 100,  False, "Set the universal nickname template. Note that ``{prefix}bind`` nicknames will override this."),
    "unverifiedRoleName":    (None,  "string", 100,  False, "Set the 'Unverified' role name -- the role that Unverified users get."),
    "shorterNicknames":      (None,  "boolean", None,False, "Brackets in group rank names will be captured instead of the full rank name, resulting in a shorter nickname."),
    "ageLimit":              (None,  "number", None, True,  "Set the minimum Roblox age in days a user must be to enter your server. People who are less than this value will be kicked."),
    "inactiveRole":          (lambda g, gd: gd.get("inactiveRole") and find(lambda r: r.id == int(gd["inactiveRole"]), g.roles), "role", None, True, "Set the role given to people who declared themselves as \"inactive\" from ``{prefix}profile``."),
    "banRelatedAccounts":    (None, "boolean", None, True,  "If this is enabled: when members are banned, their known alts are also banned from the server."),
    "unbanRelatedAccounts":  (None, "boolean", None, True,  "If this is enabled: when members are unbanned, their known alts are also unbanned from the server."),
    "disallowAlts":          (None, "boolean", None, True,  "If this is enabled: when someone joins the server and already has a linked account in the server, kick the old alt out."),
    "disallowBanEvaders":    (None, "choice", ("ban", "kick"), True,  "If this is enabled: when members join, and they have a banned account in the server, their new account will also be actioned."),
    #"groupShoutChannel":     (lambda g, gd: g.get_channel(int(gd.get("groupShoutChannel", "0"))),  None, None, True, "Group shouts will be sent to your Discord channel."),
    "whiteLabel":            (lambda g, gd: bool(gd.get("customBot")),  None, None, True,      "Modify the username and profile picture of __most__ Bloxlink responses."),
    "promptDelete":          (None, "boolean", None, False, "Toggle the deleting of prompt messages after it finishes."),
    "trelloBindMode":        (None, "choice", ("merge", "replace"), False, "Choose 'replace' if trello binds should replace the server binds, or 'merge' if trello binds should be merged with the server binds. Default = merge."),
}

DEFAULTS = {
    "prefix": "{prefix}",
    "Linked Groups": "view using ``@Bloxlink viewbinds``",
    "verifiedRoleName": "Verified",
    "verifiedRoleEnabled": True,
    "unverifiedRoleEnabled": True,
    "allowOldRoles": False,
    "autoRoles": True,
    "autoVerification": True,
    #"dmVerifications": True,
    "dynamicRoles": True,
    "persistRoles": True,
    "trelloID": "No Trello Board",
    "allowReVerify": True,
    "welcomeMessage": "Welcome to **{server-name}**, {roblox-name}! Visit <" + VERIFY_URL + "> to change your account.",
    "nicknameTemplate": "{roblox-name}",
    "unverifiedRoleName": "Unverified",
    "shorterNicknames": True,
    "ageLimit": 0,
    #"groupShoutChannel": None,
    "whiteLabel": False,
    "promptDelete": True,
    "inactiveRole": None,
    "banRelatedAccounts": False,
    "unbanRelatedAccounts": False,
    "disallowAlts": False,
    "disallowBanEvaders": False,
    #"groupRequired": True,
    "trelloBindMode": "merge"
}

ARROW = "\u2192"

MAGIC_ROLES = ["Bloxlink Admin", "Bloxlink Bypass", "Bloxlink Updater"]

OWNER = 84117866944663552

HELP_DESCRIPTION = "**Welcome to Bloxlink!**\n\n" \
                   "**Support Server:** https://blox.link/support\n" \
                   "**Website:** https://blox.link/\n" \
                   "**Invite:** https://blox.link/invite\n\n" \
                   "Please use ``{prefix}setup`` to set-up your server.\n" \
                   "Want sweet perks for your server? Check out our **[Patreon!](https://www.patreon.com/join/bloxlink?)**"


TRANSFER_COOLDOWN = 5

SERVER_INVITE = "https://discord.gg/jJKWpsr"

TABLE_STRUCTURE = {
    "bloxlink": [
        "users",
        "guilds",
        "gameVerification",
        "robloxAccounts",
        "commands",
        "miscellaneous",
        "restrictedUsers"
    ],
    "canary": [
        "guilds",
    ],
    "patreon": [
        "refreshTokens",
        "patrons"
    ]
}

LIMITS = {
    "BINDS": {
        "FREE": 60,
        "PREMIUM": 200
    },
    "BACKUPS": 4
}

PLAYING_STATUS = "Meet Bloxlink: {prefix}about"

AVATARS = {
    "PRIDE": "https://cdn.discordapp.com/attachments/480614508633522176/730969660010266644/rainbow_resized.png"
}

STREAMERS = (84117866944663552, 194962036784889858, 84388454456127488)

if RELEASE == "LOCAL":
    CACHE_CLEAR = 2
else:
    CACHE_CLEAR = 10

TIP_CHANCES = {
    "PROMPT_ERROR": 30,
    "GETROLE_DONATE": 10
}

TRELLO = {
	"CARD_LIMIT": 100,
	"LIST_LIMIT": 10,
    "TRELLO_BOARD_CACHE_EXPIRATION": 10 * 60
}