from django.contrib import admin
from django.shortcuts import render
from django.urls import path
from django.db.models import Sum, Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _, activate, get_language, check_for_language
from django.http import HttpResponseRedirect
from django.conf import settings
from datetime import datetime, timedelta

# Customize the default admin site
admin.site.site_header = _("Expense Management System")
admin.site.site_title = _("Expense Management")
admin.site.index_title = _("Welcome to Expense Management Administration")


def get_flag_icons():
    """Get flag icons for language switcher"""
    try:
        from base.models import FlagIcon
        flags = FlagIcon.objects.filter(is_active=True)
        flag_dict = {}
        for flag in flags:
            flag_dict[flag.language_code] = flag.flag_url
        return flag_dict
    except:
        # Fallback to default flags if model doesn't exist
        return {
            'en': None,
            'fa': None
        }


def get_site_branding():
    """Get site branding configuration"""
    try:
        from base.models import SiteBranding
        branding = SiteBranding.get_active()
        if branding:
            return {
                'site_title': branding.site_title,
                'site_header': branding.site_header,
                'logo_url': branding.logo.url if branding.logo else None,
                'favicon_url': branding.favicon.url if branding.favicon else None,
            }
    except:
        pass
    
    # Fallback to default branding
    return {
        'site_title': 'Expense Management',
        'site_header': 'Expense Management System',
        'logo_url': None,
        'favicon_url': None,
    }





def switch_language(request):
    """Switch language and redirect back"""
    language = request.GET.get('lang', 'en')
    if check_for_language(language):
        # Set the language in session
        request.session[settings.LANGUAGE_COOKIE_NAME] = language
        # Also set it in the request for immediate effect
        request.LANGUAGE_CODE = language
        # Activate the language for this request
        activate(language)
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/admin/'))


def get_dashboard_data():
    """Get dashboard data for the admin index page"""
    try:
        # Import here to avoid circular imports
        from expenses.models import Transaction, Expense, Income
        from categories.models import Category
        
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
        
        # Calculate totals
        total_expenses = sum(item['total'] for item in expenses_data)
        total_income = sum(item['total'] for item in income_data)
        net_amount = total_income - total_expenses
        
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
            chart_data['expenses'].append(float(expense_amount))
            
            # Find income for this date
            income_amount = next(
                (item['total'] for item in income_data if item['transacted_at__date'] == date),
                0
            )
            chart_data['income'].append(float(income_amount))
        
        # If no data, create some sample data for testing
        if not chart_data['labels']:
            from datetime import date, timedelta
            today = date.today()
            for i in range(7):
                test_date = today - timedelta(days=i)
                chart_data['labels'].append(test_date.strftime('%m/%d'))
                chart_data['expenses'].append(0.0)
                chart_data['income'].append(0.0)
            chart_data['labels'].reverse()
            chart_data['expenses'].reverse()
            chart_data['income'].reverse()
        
        # Debug: Print chart data to console
        print(f"Chart data: {chart_data}")
        print(f"Total expenses: {total_expenses}")
        print(f"Total income: {total_income}")
        
        return {
            'chart_data': chart_data,
            'total_expenses': total_expenses,
            'total_income': total_income,
            'net_amount': net_amount,
            'expense_categories': expense_categories,
            'income_categories': income_categories,
        }
    except Exception as e:
        print(f"Error in get_dashboard_data: {e}")
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
        'title': _('Financial Dashboard'),
    }
    return render(request, 'admin/dashboard.html', context)


# Add dashboard URL to admin site
original_get_urls = admin.site.get_urls

def custom_get_urls():
    urls = original_get_urls()
    custom_urls = [
        path('dashboard/', admin.site.admin_view(dashboard_view), name='dashboard'),
        path('switch-language/', admin.site.admin_view(switch_language), name='switch_language'),
    ]
    return custom_urls + urls

admin.site.get_urls = custom_get_urls 