from django.db import models
from base.models import BaseModel


class Transaction(BaseModel):
    amount = models.BigIntegerField()
    category = models.ForeignKey(to='categories.Category', related_name='transactions', on_delete=models.CASCADE)
    note = models.CharField(max_length=4000, null=True, blank=True)
    transacted_at = models.DateTimeField()

    def __str__(self):
        return f"{self.category.name} - {self.amount} ({self.transacted_at.strftime('%Y-%m-%d')})"


class Expense(Transaction):
    class Meta:
        proxy = True

    def save(self, *args, **kwargs):
        # Ensure the category is of expense type
        if self.category.type != self.category.CategoryType.EXPENSE:
            raise ValueError("Expense transactions must use expense categories")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Expense: {self.category.name} - {self.amount} ({self.transacted_at.strftime('%Y-%m-%d')})"


class Income(Transaction):
    class Meta:
        proxy = True

    def save(self, *args, **kwargs):
        # Ensure the category is of income type
        if self.category.type != self.category.CategoryType.INCOME:
            raise ValueError("Income transactions must use income categories")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Income: {self.category.name} - {self.amount} ({self.transacted_at.strftime('%Y-%m-%d')})"
