from django.contrib import admin
from .models import Workspace
from django.contrib.auth import get_user_model

User = get_user_model()

@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = ('name', 'user_count')
    search_fields = ('name',)
    filter_horizontal = ('members',)  # For ManyToManyField, nice multi-select widget

    def user_count(self, obj):
        return obj.members.count()
    user_count.short_description = "Number of Users"
