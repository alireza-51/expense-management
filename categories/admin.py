from django.contrib import admin
from unfold.admin import ModelAdmin
from django import forms
from django.utils.html import format_html
from django.forms import Widget
from categories.models import Category


class ColorPickerWidget(Widget):
    template_name = 'admin/color_picker_widget.html'
    
    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context['widget']['type'] = 'hidden'
        context['widget']['attrs']['class'] = 'color-picker-input'
        return context
    
    def render(self, name, value, attrs=None, renderer=None):
        """Fallback render method if template is not found"""
        try:
            return super().render(name, value, attrs, renderer)
        except:
            # Fallback to simple color input if template fails
            final_attrs = self.build_attrs(attrs)
            final_attrs['type'] = 'color'
            final_attrs['class'] = 'color-picker-input'
            attrs_html = ' '.join([f'{k}="{v}"' for k, v in final_attrs.items()])
            return f'<input name="{name}" value="{value or "#3B82F6"}" {attrs_html} />'


class CategoryAdminForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = '__all__'
        widgets = {
            'color': ColorPickerWidget(),
        }


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    form = CategoryAdminForm
    list_display = ['name', 'type', 'parent', 'color_display', 'description', 'created_at']
    list_filter = ['type', 'parent', 'created_at']
    search_fields = ['name', 'description']
    list_per_page = 20
    ordering = ['name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'type', 'parent', 'description', 'color')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'edited_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'edited_at']
    
    def color_display(self, obj):
        if obj.color:
            return format_html(
                '<div style="background-color: {}; width: 20px; height: 20px; border-radius: 3px; border: 1px solid #ccc;"></div>',
                obj.color
            )
        return '-'
    color_display.short_description = 'Color'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('parent')
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "parent":
            kwargs["queryset"] = Category.objects.exclude(id=request.resolver_match.kwargs.get('object_id', None))
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
