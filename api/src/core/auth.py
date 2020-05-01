from .conf import ADMIN_AUTH
from views import render

def authenticate(fn):
	def new_fn(request):
		if request.headers.get("Authorization") != ADMIN_AUTH:
			return render.json({
				"success": False,
				"error": "Invalid authorization"
			}, 403)

		return fn(request)

	return new_fn
