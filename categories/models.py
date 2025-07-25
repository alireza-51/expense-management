from django.db import models
from base.models import BaseModel

class Category(BaseModel):
    class CategoryType(models.IntegerChoices):
        EXPENSE = 1, 'خرج'
        INCOME = 2, 'درآمد'

    name = models.CharField(max_length=127, unique=True)
    icon = models.ImageField(null=True, blank=True)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='childs')
    type = models.IntegerField(choices=CategoryType.choices, default=CategoryType.EXPENSE)

    class Meta:
        verbose_name_plural = 'Categories'
    
    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"