from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Workspace

User = get_user_model()

@receiver(post_save, sender=User)
def create_user_workspace(sender, instance, created, **kwargs):
    """
    Create a default workspace whenever a new user is created.
    """
    if created:
        print('user creaetd!')
        workspace = Workspace.objects.create(
            name=f"{instance.username}'s Workspace",
            owner=instance
        )
        workspace.members.add(instance)
