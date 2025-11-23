from django.conf import settings
from .models import Workspace


class WorkspaceMiddleware:
    """
    Middleware to handle workspace selection and management.
    Requires user to be authenticated (via session or JWT).
    Should be placed after JWTAuthenticationMiddleware.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.workspace = None

        if request.user.is_authenticated:
            # 🔹 Read workspace ID from cookie (preferred) or fallback to session
            ws_id = request.COOKIES.get("workspace") or request.session.get("workspace")

            if ws_id:
                try:
                    ws = Workspace.objects.get(id=ws_id, members=request.user)
                    request.workspace = ws
                except Workspace.DoesNotExist:
                    request.workspace = None

            # 🔹 Fallback to first owned workspace
            if request.workspace is None:
                owned_ws = request.user.owned_workspaces.first()
                if owned_ws:
                    request.workspace = owned_ws

        response = self.get_response(request)

        # 🔹 Sync cookie only if authenticated and workspace set
        if request.user.is_authenticated and request.workspace:
            # Environment-aware cookie settings
            if settings.DEBUG:
                # Development: relaxed for local frontend use
                response.set_cookie(
                    "workspace",
                    str(request.workspace.id),
                    httponly=False,   # Allow JS to read (useful in dev)
                    samesite="Lax",   # Allow localhost cross-site requests
                    secure=False      # No HTTPS requirement in local dev
                )
            else:
                # Production: strict, secure
                response.set_cookie(
                    "workspace",
                    str(request.workspace.id),
                    httponly=True,    # Prevent JS access
                    samesite="None",  # Allow cross-site only if HTTPS
                    secure=True       # Only over HTTPS
                )

        return response
