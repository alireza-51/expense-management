from django.conf import settings
import logging
from .models import Workspace

logger = logging.getLogger(__name__)


class WorkspaceMiddleware:
    """
    Middleware to handle workspace selection and management.
    Requires user to be authenticated (via session or JWT).
    Should be placed after JWTAuthenticationMiddleware.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        logger.debug("[WORKSPACE_MIDDLEWARE] Initialized")

    def __call__(self, request):
        logger.debug(f"[WORKSPACE_MIDDLEWARE] Step 1: Processing request - Path: {request.path}, Method: {request.method}")
        request.workspace = None

        if request.user.is_authenticated:
            logger.debug(f"[WORKSPACE_MIDDLEWARE] Step 2: User authenticated - User ID: {request.user.id}")
            # 🔹 Read workspace ID from cookie (preferred) or fallback to session
            cookie_value = request.COOKIES.get("workspace")
            session_value = request.session.get("workspace")
            ws_id = cookie_value or session_value
            logger.debug(f"[WORKSPACE_MIDDLEWARE] Step 2.1: Workspace ID from cookie: {cookie_value}")
            logger.debug(f"[WORKSPACE_MIDDLEWARE] Step 2.1.1: All cookies received: {list(request.COOKIES.keys())}")
            logger.debug(f"[WORKSPACE_MIDDLEWARE] Step 2.2: Workspace ID from session: {session_value}")
            logger.info(f"[WORKSPACE_MIDDLEWARE] Step 2.3: Selected workspace ID: {ws_id}")

            if ws_id:
                logger.info(f"[WORKSPACE_MIDDLEWARE] Step 3: Looking up workspace with ID={ws_id} for user={request.user.id}")
                try:
                    ws = Workspace.objects.get(id=ws_id, members=request.user)
                    request.workspace = ws
                    logger.info(f"[WORKSPACE_MIDDLEWARE] Step 3.1: Workspace found - ID: {ws.id}, Name: {ws.name}")
                except Workspace.DoesNotExist:
                    logger.warning(f"[WORKSPACE_MIDDLEWARE] Step 3.1: Workspace {ws_id} not found or user is not a member")
                    request.workspace = None

            # 🔹 Fallback to first owned workspace
            if request.workspace is None:
                logger.info(f"[WORKSPACE_MIDDLEWARE] Step 4: No workspace found, checking for owned workspaces")
                owned_ws = request.user.owned_workspaces.first()
                if owned_ws:
                    request.workspace = owned_ws
                    logger.info(f"[WORKSPACE_MIDDLEWARE] Step 4.1: Using first owned workspace - ID: {owned_ws.id}, Name: {owned_ws.name}")
                else:
                    logger.warning(f"[WORKSPACE_MIDDLEWARE] Step 4.1: No owned workspaces found for user {request.user.id}")
        else:
            logger.debug(f"[WORKSPACE_MIDDLEWARE] Step 2: User not authenticated, skipping workspace selection")

        logger.debug(f"[WORKSPACE_MIDDLEWARE] Step 5: Final workspace - ID: {request.workspace.id if request.workspace else None}")
        
        response = self.get_response(request)

        # 🔹 Sync cookie only if authenticated and workspace set
        # Check if cookie was already set by a view (e.g., switch action)
        # to avoid overriding view-specific cookie settings
        cookie_already_set = 'workspace' in response.cookies
        logger.debug(f"[WORKSPACE_MIDDLEWARE] Step 6: Cookie already set by view: {cookie_already_set}")
        
        if request.user.is_authenticated and request.workspace and not cookie_already_set:
            logger.info(f"[WORKSPACE_MIDDLEWARE] Step 7: Syncing workspace cookie - Workspace ID: {request.workspace.id}")
            # Ensure CORS credentials header is set for cross-origin cookie support
            response["Access-Control-Allow-Credentials"] = "true"
            # Cookie expires in 30 days (30 * 24 * 60 * 60 seconds)
            max_age = 30 * 24 * 60 * 60
            
            # Detect if request is HTTPS (production)
            is_https = request.is_secure() or request.META.get('HTTP_X_FORWARDED_PROTO') == 'https'
            is_production = settings.IS_PRODUCTION or is_https
            
            # Environment-aware cookie settings
            if is_production:
                logger.debug(f"[WORKSPACE_MIDDLEWARE] Step 7.1: Setting cookie in PRODUCTION mode (max_age={max_age}, HTTPS={is_https})")
                # Production: strict, secure
                response.set_cookie(
                    "workspace",
                    str(request.workspace.id),
                    max_age=max_age,
                    path="/",
                    httponly=True,    # Prevent JS access
                    samesite="None",  # Allow cross-site only if HTTPS
                    secure=True       # Only over HTTPS
                )
            else:
                logger.debug(f"[WORKSPACE_MIDDLEWARE] Step 7.1: Setting cookie in DEBUG mode (max_age={max_age})")
                # Development: relaxed for local frontend use
                response.set_cookie(
                    "workspace",
                    str(request.workspace.id),
                    max_age=max_age,
                    path="/",
                    httponly=False,   # Allow JS to read (useful in dev)
                    samesite="Lax",   # Allow localhost cross-site requests
                    secure=False      # No HTTPS requirement in local dev
                )
            logger.info(f"[WORKSPACE_MIDDLEWARE] Step 7.2: Cookie synced successfully")
            # Log the actual Set-Cookie header
            set_cookie_header = response.get("Set-Cookie", "Not found")
            logger.debug(f"[WORKSPACE_MIDDLEWARE] Step 7.3: Set-Cookie header value: {set_cookie_header}")
        else:
            logger.debug(f"[WORKSPACE_MIDDLEWARE] Step 7: Skipping cookie sync - authenticated: {request.user.is_authenticated}, workspace: {request.workspace is not None}, cookie_already_set: {cookie_already_set}")

        logger.debug(f"[WORKSPACE_MIDDLEWARE] Step 8: Middleware processing complete")
        return response
