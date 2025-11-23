from typing import List
from utils.typing import MemberData
from rest_framework import serializers
from workspaces.models import Workspace, WorkspaceInvitation
from django.contrib.auth import get_user_model

User = get_user_model()


class WorkspaceSerializer(serializers.ModelSerializer):
    members = serializers.SerializerMethodField(read_only=True)  # dynamic
    owner = serializers.ReadOnlyField(source='owner.id')

    class Meta:
        model = Workspace
        fields = ['id', 'name', 'owner', 'members', 'created_at', 'edited_at']

    def get_members(self, obj) -> List[MemberData]:
        # Return a list of user ids or nested info
        return [{"id": u.id, "username": u.username} for u in obj.members.all()]

    def create(self, validated_data):
        workspace = Workspace.objects.create(owner=self.context['request'].user, **validated_data)
        # Make sure owner is always a member
        workspace.members.add(self.context['request'].user)
        return workspace


class WorkspaceInvitationSerializer(serializers.ModelSerializer):
    invited_user_username = serializers.ReadOnlyField(source='invited_user.username')
    invited_by_username = serializers.ReadOnlyField(source='invited_by.username')
    workspace_name = serializers.ReadOnlyField(source='workspace.name')
    is_accepted = serializers.ReadOnlyField()  # dynamic property

    class Meta:
        model = WorkspaceInvitation
        fields = [
            'id',
            'workspace',
            'workspace_name',
            'invited_user',
            'invited_user_username',
            'invited_by',
            'invited_by_username',
            'created_at',
            'accepted_at',
            'is_accepted',
        ]
        read_only_fields = ['invited_by', 'accepted_at', 'is_accepted']
