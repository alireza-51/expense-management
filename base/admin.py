from django.contrib import admin
from unfold.admin import ModelAdmin
from django.utils.html import format_html
from .models import FlagIcon, SiteBranding


@admin.register(SiteBranding)
class SiteBrandingAdmin(ModelAdmin):
    list_display = ['site_title', 'logo_preview', 'is_active', 'created_at']
    list_filter = ['is_active']
    readonly_fields = ['created_at', 'edited_at']
    
    fieldsets = (
        ('Branding Information', {
            'fields': ('site_title', 'site_header', 'logo', 'favicon', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'edited_at'),
            'classes': ('collapse',)
        }),
    )
    
    def logo_preview(self, obj):
        if obj.logo:
            return format_html(
                '<img src="{}" style="max-width: 100px; max-height: 50px; border: 1px solid #ccc; border-radius: 4px;" />',
                obj.logo.url
            )
        return 'No logo uploaded'
    logo_preview.short_description = 'Logo Preview'





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
