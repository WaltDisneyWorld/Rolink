from os import environ as env
import config


VALID_SECRETS = ("TRELLO_KEY", "TRELLO_TOKEN", "RETHINKDB_HOST", "RETHINKDB_PASSWORD",
                "RETHINKDB_PORT", "RETHINKDB_DB", "REDIS_HOST", "REDIS_PORT", "REDIS_PASSWORD",
                "TOKEN", "SENTRY_URL", "DBL_KEY", "TOPGG_KEY")



for secret in VALID_SECRETS:
    globals()[secret] = env.get(secret) or getattr(config, secret, "")
