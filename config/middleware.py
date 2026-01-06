from django.http import HttpResponse


class SimpleCorsMiddleware:
    """
    Minimal CORS handler for public JSON API endpoints.
    Allows specific origins configured via settings.CORS_ALLOWED_ORIGINS.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "OPTIONS":
            response = HttpResponse()
        else:
            response = self.get_response(request)

        origin = request.headers.get("Origin")
        # Pull from settings lazily to avoid import cycles
        try:
            from django.conf import settings

            cors_allowed = getattr(settings, "CORS_ALLOWED_ORIGINS", [])
        except Exception:
            cors_allowed = []

        if origin and origin in cors_allowed:
            response["Access-Control-Allow-Origin"] = origin
            response["Vary"] = "Origin"
            response["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            response["Access-Control-Allow-Headers"] = "Content-Type, Authorization, Accept"
        return response
