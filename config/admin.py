from django.contrib import admin
from django.shortcuts import render
from django.urls import path
from django.db.models import Sum, Q
from django.utils import timezone
from datetime import datetime, timedelta


# Customize the default admin site
admin.site.site_header = "Expense Management System"
admin.site.site_title = "Expense Management"
admin.site.index_title = "Welcome to Expense Management Administration"


def get_dashboard_data():
    """Get dashboard data for the admin index page"""
    try:
        # Import here to avoid circular imports
        from expenses.models import Transaction, Expense, Income
        from categories.models import Category
        
        # Debug: Check if we have any data
        total_transactions = Transaction.objects.count()
        total_expenses = Expense.objects.count()
        total_incomes = Income.objects.count()
        total_categories = Category.objects.count()
        
        print(f"Debug - Total transactions: {total_transactions}")
        print(f"Debug - Total expenses: {total_expenses}")
        print(f"Debug - Total incomes: {total_incomes}")
        print(f"Debug - Total categories: {total_categories}")
        
        # Get ALL data using the base Transaction model
        # Get expenses (transactions with expense categories)
        expenses_data = Transaction.objects.filter(
            category__type=Category.CategoryType.EXPENSE
        ).values('transacted_at__date').annotate(
            total=Sum('amount')
        ).order_by('transacted_at__date')
        
        # Get income (transactions with income categories)
        income_data = Transaction.objects.filter(
            category__type=Category.CategoryType.INCOME
        ).values('transacted_at__date').annotate(
            total=Sum('amount')
        ).order_by('transacted_at__date')
        
        print(f"Debug - Expenses data count: {len(expenses_data)}")
        print(f"Debug - Income data count: {len(income_data)}")
        
        # Get category breakdown
        expense_categories = Category.objects.filter(
            type=Category.CategoryType.EXPENSE
        ).annotate(
            total_amount=Sum('transactions__amount')
        ).filter(total_amount__isnull=False).order_by('-total_amount')[:5]
        
        income_categories = Category.objects.filter(
            type=Category.CategoryType.INCOME
        ).annotate(
            total_amount=Sum('transactions__amount')
        ).filter(total_amount__isnull=False).order_by('-total_amount')[:5]
        
        print(f"Debug - Expense categories count: {len(expense_categories)}")
        print(f"Debug - Income categories count: {len(income_categories)}")
        
        # Calculate totals
        total_expenses = sum(item['total'] for item in expenses_data)
        total_income = sum(item['total'] for item in income_data)
        net_amount = total_income - total_expenses
        
        print(f"Debug - Total expenses amount: {total_expenses}")
        print(f"Debug - Total income amount: {total_income}")
        print(f"Debug - Net amount: {net_amount}")
        
        # Prepare chart data - use all available dates
        chart_data = {
            'labels': [],
            'expenses': [],
            'income': []
        }
        
        # Get all unique dates from both expenses and income
        all_dates = set()
        for item in expenses_data:
            all_dates.add(item['transacted_at__date'])
        for item in income_data:
            all_dates.add(item['transacted_at__date'])
        
        # Sort dates
        sorted_dates = sorted(all_dates)
        
        for date in sorted_dates:
            chart_data['labels'].append(date.strftime('%m/%d'))
            
            # Find expense for this date
            expense_amount = next(
                (item['total'] for item in expenses_data if item['transacted_at__date'] == date),
                0
            )
            chart_data['expenses'].append(expense_amount)
            
            # Find income for this date
            income_amount = next(
                (item['total'] for item in income_data if item['transacted_at__date'] == date),
                0
            )
            chart_data['income'].append(income_amount)
        
        print(f"Debug - Chart labels count: {len(chart_data['labels'])}")
        print(f"Debug - Chart expenses count: {len(chart_data['expenses'])}")
        print(f"Debug - Chart income count: {len(chart_data['income'])}")
        
        return {
            'chart_data': chart_data,
            'total_expenses': total_expenses,
            'total_income': total_income,
            'net_amount': net_amount,
            'expense_categories': expense_categories,
            'income_categories': income_categories,
        }
    except Exception as e:
        print(f"Debug - Error occurred: {str(e)}")
        # Return empty data if there's an error
        return {
            'chart_data': {'labels': [], 'expenses': [], 'income': []},
            'total_expenses': 0,
            'total_income': 0,
            'net_amount': 0,
            'expense_categories': [],
            'income_categories': [],
        }


# Store the original index method
original_index = admin.site.index

def custom_index(request, extra_context=None):
    """Custom index method that includes dashboard data"""
    dashboard_data = get_dashboard_data()
    if extra_context is None:
        extra_context = {}
    extra_context.update(dashboard_data)
    return original_index(request, extra_context)

# Replace the index method
admin.site.index = custom_index


def dashboard_view(request):
    """Standalone dashboard view"""
    dashboard_data = get_dashboard_data()
    context = {
        **dashboard_data,
        'title': 'Financial Dashboard',
    }
    return render(request, 'admin/dashboard.html', context)


# Add dashboard URL to admin site
admin.site.get_urls = lambda: [
    path('dashboard/', admin.site.admin_view(dashboard_view), name='dashboard'),
] + admin.site.get_urls() 