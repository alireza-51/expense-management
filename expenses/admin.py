from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Transaction, Expense, Income


@admin.register(Transaction)
class TransactionAdmin(ModelAdmin):
    list_display = ['amount', 'category', 'note', 'transacted_at', 'created_at']
    list_filter = ['category', 'transacted_at', 'created_at']
    search_fields = ['note', 'category__name']
    list_per_page = 25
    ordering = ['-transacted_at']
    
    fieldsets = (
        ('Transaction Details', {
            'fields': ('amount', 'category', 'note', 'transacted_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'edited_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'edited_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('category')


@admin.register(Expense)
class ExpenseAdmin(ModelAdmin):
    list_display = ['amount', 'category', 'note', 'transacted_at', 'created_at']
    list_filter = ['category', 'transacted_at', 'created_at']
    search_fields = ['note', 'category__name']
    list_per_page = 25
    ordering = ['-transacted_at']
    
    fieldsets = (
        ('Expense Details', {
            'fields': ('amount', 'category', 'note', 'transacted_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'edited_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'edited_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('category').filter(
            category__type=self.model.category.field.related_model.CategoryType.EXPENSE
        )


@admin.register(Income)
class IncomeAdmin(ModelAdmin):
    list_display = ['amount', 'category', 'note', 'transacted_at', 'created_at']
    list_filter = ['category', 'transacted_at', 'created_at']
    search_fields = ['note', 'category__name']
    list_per_page = 25
    ordering = ['-transacted_at']
    
    fieldsets = (
        ('Income Details', {
            'fields': ('amount', 'category', 'note', 'transacted_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'edited_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'edited_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('category').filter(
            category__type=self.model.category.field.related_model.CategoryType.INCOME
        )
