from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from .models import Workspace

@login_required
def switch_workspace(request):
    if request.method == "POST" and request.user.is_authenticated:
        ws_id = request.POST.get('workspace_id')
        if ws_id:
            request.session['current_workspace'] = ws_id
    # Redirect back to the previous page or to admin index if no referer
    return redirect(request.META.get('HTTP_REFERER', '/'))
