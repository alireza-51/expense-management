from django.db.models import Q
from django.utils import timezone
from django.conf import settings
import logging

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from workspaces.models import Workspace, WorkspaceInvitation
from .serializers import WorkspaceSerializer, WorkspaceInvitationSerializer
from .permissions import IsOwnerOrMember

from drf_spectacular.utils import extend_schema

logger = logging.getLogger(__name__)


@extend_schema(tags=["Workspace"])
class WorkspaceViewSet(viewsets.ModelViewSet):
    serializer_class = WorkspaceSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrMember]

    def get_queryset(self):
        return Workspace.objects.filter(
            members=self.request.user
        ).distinct()

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=False, methods=['get'])
    def current(self, request):
        """
        Get the current active workspace for the authenticated user.
        """
        workspace = getattr(request, 'workspace', None)
        if not workspace:
            return Response(
                {"detail": "No workspace selected."},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = self.get_serializer(workspace)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def switch(self, request, pk=None):
        """
        Switch workspace and set cookie
        """
        logger.info(f"[SWITCH_WORKSPACE] Step 1: Request received - User: {request.user.id}, Workspace ID: {pk}")
        logger.debug(f"[SWITCH_WORKSPACE] Step 1.1: Request path: {request.path}, Method: {request.method}")
        logger.debug(f"[SWITCH_WORKSPACE] Step 1.2: User authenticated: {request.user.is_authenticated}")
        logger.debug(f"[SWITCH_WORKSPACE] Step 1.3: Request origin: {request.META.get('HTTP_ORIGIN', 'Not set')}")
        logger.debug(f"[SWITCH_WORKSPACE] Step 1.4: Request referer: {request.META.get('HTTP_REFERER', 'Not set')}")
        logger.debug(f"[SWITCH_WORKSPACE] Step 1.5: Cookies in request: {list(request.COOKIES.keys())}")
        
        # Get workspace object
        logger.info(f"[SWITCH_WORKSPACE] Step 2: Retrieving workspace object with pk={pk}")
        workspace = self.get_object()
        logger.info(f"[SWITCH_WORKSPACE] Step 2.1: Workspace found - ID: {workspace.id}, Name: {workspace.name}")
        logger.debug(f"[SWITCH_WORKSPACE] Step 2.2: Workspace owner: {workspace.owner.id if workspace.owner else None}")
        logger.debug(f"[SWITCH_WORKSPACE] Step 2.3: User is member: {request.user in workspace.members.all()}")
        
        # Check current workspace before switch
        current_workspace = getattr(request, 'workspace', None)
        logger.info(f"[SWITCH_WORKSPACE] Step 3: Current workspace - ID: {current_workspace.id if current_workspace else None}")
        
        # Create response
        logger.info(f"[SWITCH_WORKSPACE] Step 4: Creating response object")
        response = Response({"detail": f"Switched to workspace {workspace.name}"}, status=status.HTTP_200_OK)
        
        # Ensure CORS credentials header is set for cross-origin cookie support
        response["Access-Control-Allow-Credentials"] = "true"
        logger.debug(f"[SWITCH_WORKSPACE] Step 4.1: Set Access-Control-Allow-Credentials header")
        
        # Also set in session as fallback for immediate subsequent requests
        # (cookies may not be immediately available in cross-origin scenarios)
        request.session["workspace"] = str(workspace.id)
        request.session.save()
        logger.debug(f"[SWITCH_WORKSPACE] Step 4.2: Workspace also set in session: {workspace.id}")
        
        # Set cookie based on environment
        # Cookie expires in 30 days (30 * 24 * 60 * 60 seconds)
        max_age = 30 * 24 * 60 * 60
        
        # Detect if request is HTTPS (production)
        is_https = request.is_secure() or request.META.get('HTTP_X_FORWARDED_PROTO') == 'https'
        is_production = settings.IS_PRODUCTION or is_https
        
        logger.info(f"[SWITCH_WORKSPACE] Step 5: Setting workspace cookie - Production: {is_production}, HTTPS: {is_https}, DEBUG: {settings.DEBUG}")
        
        if is_production:
            logger.debug(f"[SWITCH_WORKSPACE] Step 5.1: Setting cookie in PRODUCTION mode (httponly=True, samesite=None, secure=True, max_age={max_age})")
            response.set_cookie(
                "workspace",
                str(workspace.id),
                max_age=max_age,
                path="/",
                httponly=True,
                samesite="None",
                secure=True
            )
            logger.info(f"[SWITCH_WORKSPACE] Step 5.2: Cookie set successfully - workspace={workspace.id}")
        else:
            logger.debug(f"[SWITCH_WORKSPACE] Step 5.1: Setting cookie in DEBUG mode (httponly=False, samesite=Lax, secure=False, max_age={max_age})")
            response.set_cookie(
                "workspace",
                str(workspace.id),
                max_age=max_age,
                path="/",
                httponly=False,
                samesite="Lax",
                secure=False
            )
            logger.info(f"[SWITCH_WORKSPACE] Step 5.2: Cookie set successfully - workspace={workspace.id}")
        
        # Log the actual Set-Cookie header
        set_cookie_header = response.get("Set-Cookie", "Not found")
        logger.debug(f"[SWITCH_WORKSPACE] Step 5.3: Set-Cookie header value: {set_cookie_header}")
        
        logger.info(f"[SWITCH_WORKSPACE] Step 6: Switch complete - From workspace {current_workspace.id if current_workspace else 'None'} to {workspace.id}")
        return response


@extend_schema(tags=["Workspace"])
class WorkspaceInvitationViewSet(viewsets.ModelViewSet):
    serializer_class = WorkspaceInvitationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # show invitations sent to the user or sent by the user
        return WorkspaceInvitation.objects.filter(
            Q(invited_user=self.request.user) | Q(invited_by=self.request.user)
        ).select_related('workspace', 'invited_user', 'invited_by')

    def perform_create(self, serializer):
        workspace = serializer.validated_data['workspace']
        # only owner can invite
        # TODO create roles
        if workspace.owner != self.request.user:
            raise PermissionError("Only workspace owner can invite users.")
        serializer.save(invited_by=self.request.user)

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        invitation = self.get_object()
        if invitation.invited_user != request.user:
            return Response({"detail": "Not your invitation."}, status=403)
        if invitation.is_accepted:
            return Response({"detail": "Invitation already accepted."}, status=400)

        invitation.workspace.members.add(request.user)
        invitation.accepted_at = timezone.now()
        invitation.save()
        return Response({"detail": f"Joined workspace {invitation.workspace.name}"}, status=200)

    @action(detail=True, methods=['post'])
    def decline(self, request, pk=None):
        invitation = self.get_object()
        if invitation.invited_user != request.user:
            return Response({"detail": "Not your invitation."}, status=403)
        invitation.delete()
        return Response({"detail": "Invitation declined."}, status=200)
