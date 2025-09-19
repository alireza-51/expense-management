from workspaces.models import Workspace

def current_workspace(request):
    if request.user.is_authenticated:
        ws_id = request.session.get("current_workspace")
        current_ws = None
        if ws_id:
            try:
                current_ws = Workspace.objects.get(id=ws_id)
            except Workspace.DoesNotExist:
                current_ws = None
        workspaces = Workspace.objects.filter(members=request.user)
        return {
            "current_workspace": current_ws,
            "workspaces": workspaces
        }
    return {
        "current_workspace": None,
        "workspaces": []
    }
