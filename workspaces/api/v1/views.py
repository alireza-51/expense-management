from django.db.models import Q
from django.utils import timezone
from django.conf import settings

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from workspaces.models import Workspace, WorkspaceInvitation
from .serializers import WorkspaceSerializer, WorkspaceInvitationSerializer
from .permissions import IsOwnerOrMember

from drf_spectacular.utils import extend_schema


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
        workspace = self.get_object()
        response = Response({"detail": f"Switched to workspace {workspace.name}"}, status=status.HTTP_200_OK)

        # environment-aware cookie
        if settings.DEBUG:
            response.set_cookie(
                "workspace",
                str(workspace.id),
                httponly=False,
                samesite="Lax",
                secure=False
            )
            print("DEBUG: set cookie debug mode", workspace.id)
        else:
            response.set_cookie(
                "workspace",
                str(workspace.id),
                httponly=True,
                samesite="None",
                secure=True
            )
            print("DEBUG: set cookie", workspace.id)
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
