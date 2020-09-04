from controllers import controller

def routes(app):
    app.router.add_get('/', controller.index)
    app.router.add_get('/v1/user/{id}', controller.user)
    app.router.add_get('/v1/game/{roblox_id}', controller.game_get)
    app.router.add_delete('/v1/game/{roblox_id}', controller.game_delete)
    app.router.add_post('/v1/verify/{discord_id}/{roblox_id}', controller.user_verify)
    app.router.add_get('/v1/commands/', controller.list_commands)
