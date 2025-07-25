from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Transaction, Expense, Income
from categories.models import Category
from .forms import ExpenseForm, IncomeForm, TransactionForm


@admin.register(Transaction)
class TransactionAdmin(ModelAdmin):
    form = TransactionForm
    list_display = ['amount', 'category', 'notes', 'transacted_at', 'created_at']
    list_filter = [
        'transacted_at', 
        'created_at',
        ('notes', admin.EmptyFieldListFilter),
        'category',
    ]
    search_fields = ['notes', 'category__name', 'category__parent__name']
    list_per_page = 25
    ordering = ['-transacted_at']
    list_select_related = ['category', 'category__parent']
    autocomplete_fields = ['category']
    
    fieldsets = (
        ('Transaction Details', {
            'fields': ('amount', 'category', 'notes', 'transacted_at')
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
    form = ExpenseForm
    list_display = ['amount', 'category', 'notes', 'transacted_at', 'created_at']
    list_filter = [
        'transacted_at', 
        'created_at',
        ('notes', admin.EmptyFieldListFilter),
        'category',
    ]
    search_fields = ['notes', 'category__name', 'category__parent__name']
    list_per_page = 25
    ordering = ['-transacted_at']
    list_select_related = ['category', 'category__parent']
    autocomplete_fields = ['category']
    
    fieldsets = (
        ('Expense Details', {
            'fields': ('amount', 'category', 'notes', 'transacted_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'edited_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'edited_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('category').filter(
            category__type=Category.CategoryType.EXPENSE
        )


@admin.register(Income)
class IncomeAdmin(ModelAdmin):
    form = IncomeForm
    list_display = ['amount', 'category', 'notes', 'transacted_at', 'created_at']
    list_filter = [
        'transacted_at', 
        'created_at',
        ('notes', admin.EmptyFieldListFilter),
        'category',
    ]
    search_fields = ['notes', 'category__name', 'category__parent__name']
    list_per_page = 25
    ordering = ['-transacted_at']
    list_select_related = ['category', 'category__parent']
    autocomplete_fields = ['category']
    
    fieldsets = (
        ('Income Details', {
            'fields': ('amount', 'category', 'notes', 'transacted_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'edited_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'edited_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('category').filter(
            category__type=Category.CategoryType.INCOME
        )
