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
