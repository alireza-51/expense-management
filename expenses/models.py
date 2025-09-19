from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from base.models import BaseModel
from categories.models import Category


class Transaction(BaseModel):
    workspace = models.ForeignKey(
        to='workspaces.Workspace',
        on_delete=models.CASCADE,
        related_name='transactions',
        null=True
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='transactions',
        verbose_name=_('Category')
    )
    amount = models.DecimalField(
        _('Amount'),
        max_digits=10,
        decimal_places=2
    )
    transacted_at = models.DateTimeField(_('Transaction Date'))
    notes = models.TextField(_('Notes'), blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True)

    class Meta:
        verbose_name = _('Transaction')
        verbose_name_plural = _('Transactions')
        ordering = ['-transacted_at']
    
    def __str__(self):
        return f"{self.category.name} - {self.amount} ({self.transacted_at.strftime('%Y-%m-%d')})"


class Expense(Transaction):
    class Meta:
        proxy = True
        verbose_name = _('Expense')
        verbose_name_plural = _('Expenses')
    
    def save(self, *args, **kwargs):
        if self.category.type != Category.CategoryType.EXPENSE:
            raise ValueError(_("Expense can only be associated with expense categories"))
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Expense: {self.category.name} - {self.amount} ({self.transacted_at.strftime('%Y-%m-%d')})"


class Income(Transaction):
    class Meta:
        proxy = True
        verbose_name = _('Income')
        verbose_name_plural = _('Incomes')
    
    def save(self, *args, **kwargs):
        if self.category.type != Category.CategoryType.INCOME:
            raise ValueError(_("Income can only be associated with income categories"))
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Income: {self.category.name} - {self.amount} ({self.transacted_at.strftime('%Y-%m-%d')})"
