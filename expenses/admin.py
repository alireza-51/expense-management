from django.contrib import admin
from django import forms
from unfold.admin import ModelAdmin
from .models import Transaction, Expense, Income
from categories.models import Category
from .forms import ExpenseForm, IncomeForm, TransactionForm
import jdatetime
from datetime import datetime


class AmountFormattingAdminMixin:
    """Adds formatted amount display and inline input formatter JS."""

    class Media:
        js = (
            'js/amount-format.js',
            'js/jalali-noon-default.js',
        )
        css = {
            'all': (
                'css/admin-responsive.css',
            )
        }

    @admin.display(description='Amount', ordering='amount')
    def amount_display(self, obj):
        try:
            return f"{obj.amount:,.2f}"
        except Exception:
            return obj.amount

    # Jalali date formatting helpers for list displays
    @staticmethod
    def _to_jalali_string(dt: datetime) -> str:
        if not dt:
            return "-"
        try:
            jdt = jdatetime.datetime.fromgregorian(datetime=dt)
            return jdt.strftime('%Y-%m-%d %H:%M')
        except Exception:
            return str(dt)

    @admin.display(description='Transacted At (Jalali)', ordering='transacted_at')
    def transacted_at_jalali(self, obj):
        return self._to_jalali_string(obj.transacted_at)

    @admin.display(description='Created At (Jalali)', ordering='created_at')
    def created_at_jalali(self, obj):
        return self._to_jalali_string(obj.created_at)

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.name == 'amount' and formfield is not None:
            # Ensure text input to allow commas during typing and add our class
            attrs = dict(formfield.widget.attrs)
            existing_class = attrs.get('class', '')
            attrs['class'] = (existing_class + ' amount-input').strip()
            attrs.setdefault('inputmode', 'decimal')
            attrs.setdefault('autocomplete', 'off')
            formfield.widget = forms.TextInput(attrs=attrs)
        return formfield


@admin.register(Transaction)
class TransactionAdmin(AmountFormattingAdminMixin, ModelAdmin):
    form = TransactionForm
    list_display = ['amount_display', 'category', 'notes', 'transacted_at_jalali', 'created_at_jalali']
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
class ExpenseAdmin(AmountFormattingAdminMixin, ModelAdmin):
    form = ExpenseForm
    list_display = ['amount_display', 'category', 'notes', 'transacted_at_jalali', 'created_at_jalali']
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
class IncomeAdmin(AmountFormattingAdminMixin, ModelAdmin):
    form = IncomeForm
    list_display = ['amount_display', 'category', 'notes', 'transacted_at_jalali', 'created_at_jalali']
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
