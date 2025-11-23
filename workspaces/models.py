from django.conf import settings
from django.db import models

from base.models import BaseModel

class Workspace(BaseModel):
    name = models.CharField(max_length=255)
    members = models.ManyToManyField(to=settings.AUTH_USER_MODEL, related_name='workspaces')
    owner = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        related_name='owned_workspaces',
        on_delete=models.CASCADE
    )

    def __str__(self):
        return self.name


from django.conf import settings
from django.db import models
from django.utils import timezone

class WorkspaceInvitation(models.Model):
    workspace = models.ForeignKey(
        'Workspace', on_delete=models.CASCADE, related_name='invitations'
    )
    invited_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='workspace_invitations'
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_workspace_invitations'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('workspace', 'invited_user')

    def __str__(self):
        return f"{self.invited_user.username} invited to {self.workspace.name}"

    @property
    def is_accepted(self):
        return self.accepted_at is not None

