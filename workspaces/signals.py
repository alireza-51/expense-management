from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import Workspace

User = settings.AUTH_USER_MODEL

@receiver(post_save, sender=User)
def create_user_workspace(sender, instance, created, **kwargs):
    """
    Create a default workspace whenever a new user is created.
    """
    if created:
        Workspace.objects.create(
            name=f"{instance.username}'s Workspace",
            owner=instance
        )
