from django.contrib import admin
from unfold.admin import ModelAdmin
from django.utils.html import format_html
from .models import FlagIcon


@admin.register(FlagIcon)
class FlagIconAdmin(ModelAdmin):
    list_display = ['language_code', 'flag_preview', 'is_active', 'created_at']
    list_filter = ['is_active', 'language_code']
    readonly_fields = ['created_at', 'edited_at']
    
    fieldsets = (
        ('Flag Information', {
            'fields': ('language_code', 'flag_image', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'edited_at'),
            'classes': ('collapse',)
        }),
    )
    
    def flag_preview(self, obj):
        if obj.flag_image:
            return format_html(
                '<img src="{}" style="width: 32px; height: 24px; border: 1px solid #ccc; border-radius: 4px;" />',
                obj.flag_image.url
            )
        return 'No image'
    flag_preview.short_description = 'Flag Preview'
