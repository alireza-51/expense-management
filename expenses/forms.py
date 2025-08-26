from django import forms
from .models import Expense, Income, Transaction
from categories.widgets import HierarchicalCategoryField
from categories.models import Category
from datetime import datetime as _dt
import jdatetime as _jdt

# Try to use Jalali admin widgets/fields if available; otherwise fall back to HTML5 datetime-local
try:
    from jalali_date.widgets import AdminSplitJalaliDateTime
except Exception:
    AdminSplitJalaliDateTime = None

try:
    from jalali_date.fields import SplitJalaliDateTimeField
except Exception:
    SplitJalaliDateTimeField = None

def jalali_datetime_widget():
    if AdminSplitJalaliDateTime:
        try:
            return AdminSplitJalaliDateTime()
        except Exception:
            pass
    return forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'})


class _TransactedAtCleanMixin:
    """Fallback parser: if we didn't get a datetime object, try parsing Jalali string and convert to Gregorian."""

    def clean_transacted_at(self):
        value = self.cleaned_data.get('transacted_at')
        # If field is jalali-aware, value is already a datetime
        if isinstance(value, _dt):
            return value
        # If it's a string, try to parse gracefully
        if isinstance(value, str):
            text = value.strip()
            # Try ISO (from HTML5 datetime-local)
            try:
                return _dt.fromisoformat(text)
            except Exception:
                pass
            # Try common Jalali formats
            if _jdt:
                for fmt in ('%Y-%m-%d %H:%M', '%Y/%m/%d %H:%M', '%Y-%m-%d', '%Y/%m/%d'):
                    try:
                        jdt = _jdt.datetime.strptime(text, fmt)
                        return jdt.togregorian()
                    except Exception:
                        continue
        return value


class TransactionForm(_TransactedAtCleanMixin, forms.ModelForm):
    """Custom form for Transaction with hierarchical category selection"""
    
    category = HierarchicalCategoryField(
        label='Category',
        help_text='Select a main category or subcategory'
    )

    # If available, use a Jalali-aware datetime field so conversion happens automatically
    if AdminSplitJalaliDateTime and SplitJalaliDateTimeField:
        transacted_at = SplitJalaliDateTimeField(widget=AdminSplitJalaliDateTime())
    
    class Meta:
        model = Transaction
        fields = ['amount', 'category', 'notes', 'transacted_at']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'transacted_at': jalali_datetime_widget(),
        }


class ExpenseForm(_TransactedAtCleanMixin, forms.ModelForm):
    """Custom form for Expense with hierarchical category selection"""
    
    category = HierarchicalCategoryField(
        category_type=Category.CategoryType.EXPENSE,
        label='Category',
        help_text='Select a main category or subcategory'
    )

    if AdminSplitJalaliDateTime and SplitJalaliDateTimeField:
        transacted_at = SplitJalaliDateTimeField(widget=AdminSplitJalaliDateTime())
    
    class Meta:
        model = Expense
        fields = ['amount', 'category', 'notes', 'transacted_at']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'transacted_at': jalali_datetime_widget(),
        }
    
    def clean_category(self):
        """Ensure the selected category is an expense category"""
        category = self.cleaned_data['category']
        if category and category.type != Category.CategoryType.EXPENSE:
            raise forms.ValidationError("Please select an expense category.")
        return category


class IncomeForm(_TransactedAtCleanMixin, forms.ModelForm):
    """Custom form for Income with hierarchical category selection"""
    
    category = HierarchicalCategoryField(
        category_type=Category.CategoryType.INCOME,
        label='Category',
        help_text='Select a main category or subcategory'
    )

    if AdminSplitJalaliDateTime and SplitJalaliDateTimeField:
        transacted_at = SplitJalaliDateTimeField(widget=AdminSplitJalaliDateTime())
    
    class Meta:
        model = Income
        fields = ['amount', 'category', 'notes', 'transacted_at']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'transacted_at': jalali_datetime_widget(),
        }
    
    def clean_category(self):
        """Ensure the selected category is an income category"""
        category = self.cleaned_data['category']
        if category and category.type != Category.CategoryType.INCOME:
            raise forms.ValidationError("Please select an income category.")
        return category 