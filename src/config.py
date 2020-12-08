from resources.constants import RELEASE, IS_DOCKER # pylint: disable=import-error


MODULE_DIR = [
	"src/resources/modules",
	"src/resources/events",
	"src/commands"
]


PREFIX = "!"

WEBHOOKS = { # discord webhook links
	"LOGS":  None,
	"ERRORS": None
}

PROMPT = {
	"PROMPT_TIMEOUT": 300,
	"PROMPT_ERROR_COUNT": 5
}

HTTP_RETRY_LIMIT = 5

WORDS = [
	"bus",
	"roblox",
	"book",
	"key",
	"shirt",
	"pants",
	"battery",
	"lamp",
	"desk",
	"water",
	"soda",
	"button",
	"can",
	"hello",
	"mouse",
	"vase",
	"rug",
	"blanket",
	"pillow",
	"music",
	"lego",
	"glasses",
	"controller",
	"pencil"
]

REACTIONS = { # discord emote mention strings
	"LOADING": "<a:BloxlinkLoading:530113171734921227>",
	"DONE": "<:BloxlinkSuccess:506622931791773696>",
	"DONE_ANIMATED": "<a:BloxlinkDone:528252043211571210>",
	"ERROR": "<:BloxlinkError:506622933226225676>",
	"VERIFIED": "<a:Verified:734628839581417472>",
	"BANNED": "<:ban:476838302092230672>"
}

VERIFYALL_MAX_SCAN = 5 # max concurrent !verifyall scans

if RELEASE == "LOCAL" and not IS_DOCKER: # needed for easy local tests without spawning Docker
	RETHINKDB = {
		"HOST": "rethinkdb",
		"PASSWORD": "1",
		"PORT": 28015,
		"DB": "bloxlink"
	}

	REDIS = {
		"HOST": "1",
		"PORT": 1,
		"PASSWORD": "1",
	}

	TRELLO = {
		"KEY": "1",
		"TOKEN": "1",
		"TRELLO_BOARD_CACHE_EXPIRATION": 5 * 60,
		"CARD_LIMIT": 100,
		"LIST_LIMIT": 10
	}

	TOKEN = "1"

BLOXLINK_GUILD = RELEASE == "LOCAL" and 439265180988211211 or 372036754078826496
