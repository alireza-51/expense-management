from django.contrib import admin
from unfold.admin import ModelAdmin
from categories.models import Category


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ['name', 'type', 'parent', 'created_at', 'edited_at']
    list_filter = ['type', 'parent', 'created_at']
    search_fields = ['name']
    list_per_page = 20
    ordering = ['name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'type', 'parent')
        }),
        ('Media', {
            'fields': ('icon',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'edited_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'edited_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('parent')
