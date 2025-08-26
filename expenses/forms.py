from django import forms
from .models import Expense, Income, Transaction
from categories.widgets import HierarchicalCategoryField
from categories.models import Category

# Try to use Jalali admin widgets if available; otherwise fall back to HTML5 datetime-local
try:
    from jalali_date.widgets import AdminSplitJalaliDateTime
except Exception:
    AdminSplitJalaliDateTime = None


def jalali_datetime_widget():
    if AdminSplitJalaliDateTime:
        try:
            return AdminSplitJalaliDateTime()
        except Exception:
            pass
    return forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'})


class TransactionForm(forms.ModelForm):
    """Custom form for Transaction with hierarchical category selection"""
    
    category = HierarchicalCategoryField(
        label='Category',
        help_text='Select a main category or subcategory'
    )
    
    class Meta:
        model = Transaction
        fields = ['amount', 'category', 'notes', 'transacted_at']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'transacted_at': jalali_datetime_widget(),
        }


class ExpenseForm(forms.ModelForm):
    """Custom form for Expense with hierarchical category selection"""
    
    category = HierarchicalCategoryField(
        category_type=Category.CategoryType.EXPENSE,
        label='Category',
        help_text='Select a main category or subcategory'
    )
    
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


class IncomeForm(forms.ModelForm):
    """Custom form for Income with hierarchical category selection"""
    
    category = HierarchicalCategoryField(
        category_type=Category.CategoryType.INCOME,
        label='Category',
        help_text='Select a main category or subcategory'
    )
    
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