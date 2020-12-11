from resources.constants import RELEASE, IS_DOCKER # pylint: disable=import-error


MODULE_DIR = [ # load these modules
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
	RETHINKDB_HOST = "rethinkdb"
	RETHINKDB_PASSWORD = None
	RETHINKDB_PORT = 28015
	RETHINKDB_DB = "bloxlink"

	REDIS_HOST = "redis"
	REDIS_PORT = 6379
	REDIS_PASSWORD = None

	TOKEN = None

BLOXLINK_GUILD = None # your guild ID, used to load nitro boosters and other data
