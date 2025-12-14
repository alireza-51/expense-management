from django.db import models
from django.utils.translation import gettext_lazy as _
from base.models import BaseModel
from .color_utils import get_category_color, calculate_child_color, get_root_color


class Category(BaseModel):
    class CategoryType(models.TextChoices):
        EXPENSE = 'expense', _('Expense')
        INCOME = 'income', _('Income')
    
    name = models.CharField(_('Name'), max_length=100)
    type = models.CharField(
        _('Type'),
        max_length=10,
        choices=CategoryType.choices,
        default=CategoryType.EXPENSE
    )
    description = models.TextField(_('Description'), blank=True)
    color = models.CharField(_('Color'), max_length=7, default='#3B82F6')
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name=_('Parent Category')
    )
    
    class Meta:
        verbose_name = _('Category')
        verbose_name_plural = _('Categories')
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"
    
    def calculate_color(self) -> str:
        """
        Calculate the appropriate color for this category based on hierarchy rules.
        
        Returns:
            Hex color string
        """
        if self.parent is None:
            # Root category - use distinct color based on ID
            if self.pk:
                return get_root_color(self.pk - 1)
            else:
                # Not saved yet, use a default
                return get_root_color(0)
        else:
            # Child category - derive from parent
            parent_color = self.parent.color
            
            # Get all siblings (same parent) sorted by ID
            siblings = Category.objects.filter(
                parent=self.parent,
                type=self.type
            ).order_by('id').values_list('id', flat=True)
            
            sibling_ids = list(siblings)
            
            return calculate_child_color(
                parent_color=parent_color,
                sibling_id=self.pk if self.pk else 0,
                sibling_ids=sibling_ids
            )
    
    def save(self, *args, auto_calculate_color=False, **kwargs):
        """
        Save the category, optionally auto-calculating color if not explicitly set.
        
        Args:
            auto_calculate_color: If True, calculate color automatically based on hierarchy
        """
        # Auto-calculate color if requested and parent or ID changed
        if auto_calculate_color:
            # Only calculate if this is a new object or parent changed
            if not self.pk or (self.pk and self.parent_id):
                # Check if we need to recalculate
                if self.pk:
                    # Existing object - check if parent changed
                    try:
                        old = Category.objects.get(pk=self.pk)
                        if old.parent_id != self.parent_id:
                            # Parent changed, recalculate
                            self.color = self.calculate_color()
                    except Category.DoesNotExist:
                        # New object
                        self.color = self.calculate_color()
                else:
                    # New object
                    self.color = self.calculate_color()
        
        super().save(*args, **kwargs)
        
        # After save, if this was a new object or parent changed, 
        # we may need to recalculate sibling colors
        if auto_calculate_color and self.parent:
            # Recalculate colors for all siblings to ensure proper ordering
            siblings = Category.objects.filter(
                parent=self.parent,
                type=self.type
            ).exclude(pk=self.pk).order_by('id')
            
            parent_color = self.parent.color
            all_sibling_ids = list(
                Category.objects.filter(
                    parent=self.parent,
                    type=self.type
                ).order_by('id').values_list('id', flat=True)
            )
            
            for sibling in siblings:
                new_color = calculate_child_color(
                    parent_color=parent_color,
                    sibling_id=sibling.pk,
                    sibling_ids=all_sibling_ids
                )
                if sibling.color != new_color:
                    Category.objects.filter(pk=sibling.pk).update(color=new_color)