from os import environ as env
import config


VALID_SECRETS = ("TRELLO_KEY", "TRELLO_TOKEN", "RETHINKDB_HOST", "RETHINKDB_PASSWORD",
                "RETHINKDB_PORT", "RETHINKDB_DB", "REDIS_HOST", "REDIS_PORT", "REDIS_PASSWORD",
                "TOKEN", "SENTRY_URL", "DBL_KEY", "TOPGG_KEY")


try:
    from config import TRELLO
except ImportError:
    TRELLO = {
        "KEY": env.get("TRELLO_KEY"),
        "TOKEN": env.get("TRELLO_TOKEN"),
        "TRELLO_BOARD_CACHE_EXPIRATION": 5 * 60,
        "CARD_LIMIT": 100,
        "LIST_LIMIT": 10
    }

    env["TRELLO_KEY"] = "REDACTED"
    env["TRELLO_TOKEN"] = "REDACTED"


try:
    from config import RETHINKDB
except ImportError:
    RETHINKDB = {
        "HOST": env.get("RETHINKDB_HOST"),
        "PASSWORD": env.get("RETHINKDB_PASSWORD"),
        "PORT": int(env.get("RETHINKDB_PORT")),
        "DB": env.get("RETHINKDB_DB")
    }

    env["RETHINKDB_HOST"] = "REDACTED"
    env["RETHINKDB_PASSWORD"] = "REDACTED"
    env["RETHINKDB_PORT"] = "REDACTED"
    env["RETHINKDB_DB"] = "REDACTED"


try:
    from config import REDIS
except ImportError:
    REDIS = {
        "HOST": env.get("REDIS_HOST"),
        "PORT": int(env.get("REDIS_PORT")),
        "PASSWORD": env.get("REDIS_PASSWORD"),
    }

    env["REDIS_HOST"] = "REDACTED"
    env["REDIS_PORT"] = "REDACTED"
    env["REDIS_PASSWORD"] = "REDACTED"


TOKEN = env.get("TOKEN") or getattr(config, "TOKEN")
env["TOKEN"] = "REDACTED"

SENTRY_URL = env.get("SENTRY_URL") or getattr(config, "SENTRY_URL")
env["SENTRY_URL"] = "REDACTED"

TOPGG_KEY = env.get("TOPGG_KEY") or getattr(config, "TOPGG_KEY", "")
env["TOPGG_KEY"] = "REDACTED"

DBL_KEY = env.get("DBL_KEY") or getattr(config, "DBL_KEY", "")
env["DBL_KEY"] = "REDACTED"