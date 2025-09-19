from .models import Workspace

class WorkspaceMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.current_workspace = None
        print(request.session.get("current_workspace"))

        if request.user.is_authenticated:
            ws_id = request.session.get("current_workspace")

            if ws_id:
                # Try to use the workspace in the session if the user is a member
                try:
                    ws = Workspace.objects.get(id=ws_id, members=request.user)
                    request.current_workspace = ws
                except Workspace.DoesNotExist:
                    request.current_workspace = None

            # If no valid workspace in session, fallback to a workspace the user owns
            if request.current_workspace is None:
                owned_ws = request.user.owned_workspaces.first()
                if owned_ws:
                    request.current_workspace = owned_ws
                    request.session["current_workspace"] = owned_ws.id

        return self.get_response(request)
