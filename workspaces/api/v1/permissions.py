from rest_framework import permissions


class IsOwnerOrMember(permissions.BasePermission):
    """
    Custom permission: allow only members or owners to access workspace.
    """

    def has_object_permission(self, request, view, obj):
        return request.user == obj.owner or request.user in obj.members.all()
