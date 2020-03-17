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
    "{disable-nicknaming} \u2192 overrides all other options and returns a blank nickname"
)

OPTIONS = {                # fn,  type
    "prefix":              (None, "string", 10),   #
    "verifiedRoleName":    (None, "string", 20),
    "verifiedRoleEnabled": (None, "boolean"),      #
    "Linked Groups":       (None,  None),          #
    "allowOldRoles":       (None, "boolean"),      #
    "autoRoles":           (None, "boolean"),      #
    "autoVerification":    (None, "boolean"),      #
    "dynamicRoles":        (None, "boolean"),      #
    "welcomeMessage":      (None, "string", 1500),
    "joinDM":              (None, "boolean"),
    "persistRoles":        (None, "boolean"),
    "groupLocked":         (None, "boolean"),
    "allowReVerify":       (None, "boolean"),
    "trelloID":            (None,  None)           #
}

DEFAULTS = {
    "prefix": "!",
    "Linked Groups": "view using ``@Bloxlink viewbinds``",
    "verifiedRoleName": "Verified",
    "verifiedRoleEnabled": True,
    "joinDM": True,
    "autoRoles": True,
    "autoVerification": True,
    "dynamicRoles": True,
    "trelloID": "No Trello Board",
    "allowReVerify": True,
    "welcomeMessage": "Welcome to **{server-name}**, {roblox-name}!"

}

ARROW = "\u2192"

MAGIC_ROLES = ["Bloxlink Admin", "Bloxlink Bypass", "Bloxlink Updater"]
