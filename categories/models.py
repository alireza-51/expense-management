from django.db import models
from django.utils.translation import gettext_lazy as _
from base.models import BaseModel


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