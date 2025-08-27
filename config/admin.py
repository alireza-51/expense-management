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


def get_dashboard_data(request=None, month_offset=0, specific_date=None):
    """Get dashboard data for the admin index page"""
    try:
        # Import here to avoid circular imports
        from expenses.models import Transaction, Expense, Income
        from categories.models import Category
        from base.utils import get_month_range, format_date_for_display, get_month_title
        
        # Get month range based on calendar type setting and navigation
        calendar_type = getattr(settings, 'CALENDAR_TYPE', 'gregorian')
        start_date, end_date = get_month_range(calendar_type, month_offset, specific_date)
        
        # Get current month data using the base Transaction model
        # Get expenses (transactions with expense categories) for current month
        expenses_data = Transaction.objects.filter(
            category__type=Category.CategoryType.EXPENSE,
            transacted_at__date__gte=start_date,
            transacted_at__date__lte=end_date
        ).values('transacted_at__date').annotate(
            total=Sum('amount')
        ).order_by('transacted_at__date')
        
        # Get income (transactions with income categories) for current month
        income_data = Transaction.objects.filter(
            category__type=Category.CategoryType.INCOME,
            transacted_at__date__gte=start_date,
            transacted_at__date__lte=end_date
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
        total_expenses = sum(float(item['total']) for item in expenses_data)
        total_income = sum(float(item['total']) for item in income_data)
        net_amount = total_income - total_expenses
        
        # Prepare chart data for Plotly - include all data points including zeros
        chart_data = {
            'dates': [],
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
            # Find expense for this date
            expense_amount = next(
                (item['total'] for item in expenses_data if item['transacted_at__date'] == date),
                0
            )
            
            # Find income for this date
            income_amount = next(
                (item['total'] for item in income_data if item['transacted_at__date'] == date),
                0
            )
            
            # Add all data points to Plotly chart (including zeros)
            chart_data['dates'].append(date.strftime('%Y-%m-%d'))
            chart_data['expenses'].append(float(expense_amount))
            chart_data['income'].append(float(income_amount))
        
        # If no data, create some sample data for testing
        # if not chart_data['dates']:
        #     print("No financial data available for the selected month - showing sample data")
        #     from datetime import date, timedelta
        #     today = date.today()
        #     for i in range(7):
        #         test_date = today - timedelta(days=i)
        #         chart_data['dates'].append(test_date.strftime('%Y-%m-%d'))
        #         chart_data['expenses'].append(1000.0 + (i * 500))  # Sample expense data
        #         chart_data['income'].append(2000.0 + (i * 300))   # Sample income data
        #     chart_data['dates'].reverse()
        #     chart_data['expenses'].reverse()
        #     chart_data['income'].reverse()
        
        # Debug: Print chart data to console
        print(f"Calendar type: {calendar_type}")
        print(f"Start date: {start_date}, End date: {end_date}")
        print(f"Number of expense records: {len(expenses_data)}")
        print(f"Number of income records: {len(income_data)}")
        print(f"Chart dates: {chart_data['dates']}")
        print(f"Chart expenses: {chart_data['expenses']}")
        print(f"Chart income: {chart_data['income']}")
        print(f"Total expenses: {total_expenses}")
        print(f"Total income: {total_income}")
        
        return {
            'chart_data': chart_data,
            'total_expenses': total_expenses,
            'total_income': total_income,
            'net_amount': net_amount,
            'expense_categories': expense_categories,
            'income_categories': income_categories,
            'current_month_title': get_month_title(calendar_type, month_offset, specific_date),
        }
    except Exception as e:
        print(f"Error in get_dashboard_data: {e}")
        # Return empty data if there's an error
        return {
            'chart_data': {'dates': [], 'expenses': [], 'income': []},
            'total_expenses': 0,
            'total_income': 0,
            'net_amount': 0,
            'expense_categories': [],
            'income_categories': [],
            'current_month_title': get_month_title(calendar_type) if 'calendar_type' in locals() else 'Current Month',
        }


def get_hierarchical_category_data(category_type, start_date, end_date, category_filter=None, min_amount=None, max_amount=None):
    """Get hierarchical category data for pie chart visualization"""
    from categories.models import Category
    from expenses.models import Transaction
    from django.db.models import Sum, Q
    
    # Base query for transactions in the date range
    base_query = Q(
        transactions__transacted_at__date__gte=start_date,
        transactions__transacted_at__date__lte=end_date
    )
    
    # Apply amount filters if provided
    if min_amount:
        try:
            base_query = base_query & Q(transactions__amount__gte=float(min_amount))
        except ValueError:
            pass
    
    if max_amount:
        try:
            base_query = base_query & Q(transactions__amount__lte=float(max_amount))
        except ValueError:
            pass
    
    # Get main categories (no parent) and calculate total amounts from their children
    main_categories = Category.objects.filter(
        type=category_type,
        parent__isnull=True
    ).annotate(
        total_amount=Sum('children__transactions__amount', filter=Q(
            children__transactions__transacted_at__date__gte=start_date,
            children__transactions__transacted_at__date__lte=end_date
        ))
    ).filter(total_amount__isnull=False, total_amount__gt=0).order_by('-total_amount')
    
    # If a specific category filter is applied, only show that category and its children
    if category_filter:
        try:
            category_id = int(category_filter)
            filtered_category = Category.objects.get(id=category_id)
            if filtered_category.parent:
                # If filtered category has a parent, show the parent and its children
                main_categories = Category.objects.filter(
                    id=filtered_category.parent.id
                ).annotate(
                    total_amount=Sum('children__transactions__amount', filter=Q(
                        children__transactions__transacted_at__date__gte=start_date,
                        children__transactions__transacted_at__date__lte=end_date
                    ))
                ).filter(total_amount__isnull=False, total_amount__gt=0)
            else:
                # If filtered category is a main category, show only that category
                main_categories = main_categories.filter(id=category_id)
        except (ValueError, Category.DoesNotExist):
            pass
    
    # Prepare data for pie chart
    pie_data = []
    for category in main_categories:
        # Get children categories with their amounts
        children_data = []
        children = Category.objects.filter(
            parent=category,
            type=category_type
        ).annotate(
            total_amount=Sum('transactions__amount', filter=base_query)
        ).filter(total_amount__isnull=False, total_amount__gt=0).order_by('-total_amount')
        
        for child in children:
            children_data.append({
                'id': child.id,
                'name': child.name,
                'amount': float(child.total_amount),
                'color': child.color,
                'percentage': (float(child.total_amount) / float(category.total_amount)) * 100 if category.total_amount > 0 else 0
            })
        
        pie_data.append({
            'id': category.id,
            'name': category.name,
            'amount': float(category.total_amount),
            'color': category.color,
            'percentage': 0,  # Will be calculated in template
            'children': children_data
        })
    
    # Calculate percentages
    total_amount = sum(item['amount'] for item in pie_data)
    for item in pie_data:
        item['percentage'] = (item['amount'] / total_amount) * 100 if total_amount > 0 else 0
    
    return pie_data


def get_statistics_data(request=None, month_offset=0, expense_category_filter=None, income_category_filter=None, min_amount=None, max_amount=None):
    """Get detailed statistics data for the statistics page"""
    try:
        # Import here to avoid circular imports
        from expenses.models import Transaction, Expense, Income
        from categories.models import Category
        from base.utils import get_month_range, get_month_title
        from django.db.models import Sum, Avg, Count, Q
        from datetime import datetime, timedelta
        import calendar
        
        # Get month range
        calendar_type = getattr(settings, 'CALENDAR_TYPE', 'gregorian')
        start_date, end_date = get_month_range(calendar_type, month_offset)
        
        # Get current month data
        current_month_transactions = Transaction.objects.filter(
            transacted_at__date__gte=start_date,
            transacted_at__date__lte=end_date
        )
        
        # Get previous month data for comparison
        prev_start_date = start_date - timedelta(days=30)
        prev_end_date = start_date - timedelta(days=1)
        prev_month_transactions = Transaction.objects.filter(
            transacted_at__date__gte=prev_start_date,
            transacted_at__date__lte=prev_end_date
        )
        
        # Calculate basic metrics
        current_expenses = current_month_transactions.filter(
            category__type=Category.CategoryType.EXPENSE
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        current_income = current_month_transactions.filter(
            category__type=Category.CategoryType.INCOME
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        prev_expenses = prev_month_transactions.filter(
            category__type=Category.CategoryType.EXPENSE
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        prev_income = prev_month_transactions.filter(
            category__type=Category.CategoryType.INCOME
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Convert to float to avoid decimal operations
        current_expenses = float(current_expenses)
        current_income = float(current_income)
        prev_expenses = float(prev_expenses)
        prev_income = float(prev_income)
        
        # Calculate savings rate
        savings_rate = 0
        if current_income > 0:
            savings_rate = ((current_income - current_expenses) / current_income) * 100
        
        # Calculate trends
        expense_trend = ((current_expenses - prev_expenses) / prev_expenses * 100) if prev_expenses > 0 else 0
        income_trend = ((current_income - prev_income) / prev_income * 100) if prev_income > 0 else 0
        
        # Get top spending categories
        top_expense_categories = Category.objects.filter(
            type=Category.CategoryType.EXPENSE
        ).annotate(
            total_amount=Sum('transactions__amount'),
            transaction_count=Count('transactions')
        ).filter(
            transactions__transacted_at__date__gte=start_date,
            transactions__transacted_at__date__lte=end_date
        ).order_by('-total_amount')[:5]
        
        # Get hierarchical category data for pie chart
        hierarchical_expense_data = get_hierarchical_category_data(
            Category.CategoryType.EXPENSE, 
            start_date, 
            end_date,
            expense_category_filter,
            min_amount,
            max_amount
        )
        
        # Get top income categories
        top_income_categories = Category.objects.filter(
            type=Category.CategoryType.INCOME
        ).annotate(
            total_amount=Sum('transactions__amount'),
            transaction_count=Count('transactions')
        ).filter(
            transactions__transacted_at__date__gte=start_date,
            transactions__transacted_at__date__lte=end_date
        ).order_by('-total_amount')[:5]
        
        # Calculate daily averages
        days_in_month = (end_date - start_date).days + 1
        daily_expense_avg = current_expenses / days_in_month if days_in_month > 0 else 0
        daily_income_avg = current_income / days_in_month if days_in_month > 0 else 0
        
        # Get spending patterns by day of week
        day_of_week_spending = current_month_transactions.filter(
            category__type=Category.CategoryType.EXPENSE
        ).extra(
            select={'day_of_week': "EXTRACT(dow FROM transacted_at)"}
        ).values('day_of_week').annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('day_of_week')
        
        # Generate recommendations
        recommendations = []
        
        if expense_trend > 10:
            recommendations.append({
                'type': 'warning',
                'title': 'Expense Increase Alert',
                'message': f'Your expenses have increased by {expense_trend:.1f}% compared to last month. Consider reviewing your spending habits.'
            })
        
        if current_expenses > current_income:
            recommendations.append({
                'type': 'danger',
                'title': 'Negative Cash Flow',
                'message': 'Your expenses exceed your income this month. Focus on reducing expenses or increasing income.'
            })
        
        # Find highest spending category
        if top_expense_categories:
            top_category = top_expense_categories[0]
            top_category_amount = float(top_category.total_amount)
            if top_category_amount > current_expenses * 0.4:  # More than 40% of total expenses
                recommendations.append({
                    'type': 'info',
                    'title': 'High Category Concentration',
                    'message': f'{top_category.name} accounts for {top_category_amount/current_expenses*100:.1f}% of your expenses. Consider diversifying your spending.'
                })
        
        # Savings recommendation
        if current_income > current_expenses:
            savings_rate = (current_income - current_expenses) / current_income * 100
            if savings_rate < 20:
                recommendations.append({
                    'type': 'success',
                    'title': 'Savings Opportunity',
                    'message': f'You\'re saving {savings_rate:.1f}% of your income. Aim for 20% or more for better financial security.'
                })
        
        # Budget tracking data
        budget_data = {
            'total_budget': current_income * 0.8,  # Assume 80% of income as budget
            'actual_spending': current_expenses,
            'remaining_budget': (current_income * 0.8) - current_expenses,
            'budget_utilization': (current_expenses / (current_income * 0.8)) * 100 if current_income > 0 else 0
        }
        
        # Get detailed transaction lists with filters applied at database level
        expense_transactions = current_month_transactions.filter(
            category__type=Category.CategoryType.EXPENSE
        ).select_related('category')
        
        income_transactions = current_month_transactions.filter(
            category__type=Category.CategoryType.INCOME
        ).select_related('category')
        
        # Apply category filters
        if expense_category_filter:
            try:
                expense_category_id = int(expense_category_filter)
                expense_transactions = expense_transactions.filter(category_id=expense_category_id)
            except (ValueError, TypeError):
                pass
        
        if income_category_filter:
            try:
                income_category_id = int(income_category_filter)
                income_transactions = income_transactions.filter(category_id=income_category_id)
            except (ValueError, TypeError):
                pass
        
        # Apply amount filters
        if min_amount:
            try:
                min_amount_float = float(min_amount)
                expense_transactions = expense_transactions.filter(amount__gte=min_amount_float)
                income_transactions = income_transactions.filter(amount__gte=min_amount_float)
            except ValueError:
                pass
        
        if max_amount:
            try:
                max_amount_float = float(max_amount)
                expense_transactions = expense_transactions.filter(amount__lte=max_amount_float)
                income_transactions = income_transactions.filter(amount__lte=max_amount_float)
            except ValueError:
                pass
        
        # Order the transactions
        expense_transactions = expense_transactions.order_by('-transacted_at')
        income_transactions = income_transactions.order_by('-transacted_at')
        
        # Time-based analysis
        time_analysis = {
            'monthly_trend': {
                'current_month': current_expenses,
                'previous_month': prev_expenses,
                'change_percentage': expense_trend
            },
            'daily_averages': {
                'expenses': daily_expense_avg,
                'income': daily_income_avg
            },
            'peak_spending_day': max(day_of_week_spending, key=lambda x: x['total']) if day_of_week_spending else None
        }
        
        return {
            'current_month_title': get_month_title(calendar_type, month_offset),
            'basic_metrics': {
                'total_expenses': current_expenses,
                'total_income': current_income,
                'net_amount': current_income - current_expenses,
                'expense_trend': expense_trend,
                'income_trend': income_trend,
                'savings_rate': savings_rate
            },
            'top_expense_categories': top_expense_categories,
            'top_income_categories': top_income_categories,
            'hierarchical_expense_data': hierarchical_expense_data,
            'recommendations': recommendations,
            'budget_data': budget_data,
            'time_analysis': time_analysis,
            'day_of_week_spending': day_of_week_spending,
            'expense_transactions': expense_transactions,
            'income_transactions': income_transactions
        }
        
    except Exception as e:
        print(f"Error in get_statistics_data: {e}")
        return {
            'current_month_title': 'Current Month',
            'basic_metrics': {'total_expenses': 0, 'total_income': 0, 'net_amount': 0, 'expense_trend': 0, 'income_trend': 0},
            'top_expense_categories': [],
            'top_income_categories': [],
            'recommendations': [],
            'budget_data': {'total_budget': 0, 'actual_spending': 0, 'remaining_budget': 0, 'budget_utilization': 0},
            'time_analysis': {'monthly_trend': {}, 'daily_averages': {}, 'peak_spending_day': None},
            'day_of_week_spending': []
        }


# Store the original index method
original_index = admin.site.index

def custom_index(request, extra_context=None):
    """Custom index method that includes dashboard data"""
    # Get month navigation parameters
    month_offset = int(request.GET.get('month_offset', 0))
    specific_date = request.GET.get('date', None)
    
    dashboard_data = get_dashboard_data(request, month_offset, specific_date)
    
    if extra_context is None:
        extra_context = {}
    extra_context.update(dashboard_data)
    extra_context['month_offset'] = month_offset
    extra_context['specific_date'] = specific_date
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


def statistics_view(request):
    """Detailed statistics view"""
    # Get month navigation parameters
    month_offset = int(request.GET.get('month_offset', 0))
    
    # Get filter parameters
    expense_category_filter = request.GET.get('expense_category', '')
    income_category_filter = request.GET.get('income_category', '')
    min_amount = request.GET.get('min_amount', '')
    max_amount = request.GET.get('max_amount', '')
    

    
    # Get statistics data with filters applied
    stats_data = get_statistics_data(
        request, 
        month_offset, 
        expense_category_filter, 
        income_category_filter, 
        min_amount, 
        max_amount
    )
    
    # Get filtered transactions from stats_data
    expense_transactions = stats_data.get('expense_transactions', [])
    income_transactions = stats_data.get('income_transactions', [])
    
    # Get all categories for filter dropdowns
    from categories.models import Category
    expense_categories = Category.objects.filter(type=Category.CategoryType.EXPENSE).order_by('name')
    income_categories = Category.objects.filter(type=Category.CategoryType.INCOME).order_by('name')
    
    import json
        
    context = {
        'title': _('Financial Statistics'),
        'month_offset': month_offset,
        'expense_category_filter': expense_category_filter,
        'income_category_filter': income_category_filter,
        'min_amount': min_amount,
        'max_amount': max_amount,
        'expense_categories': expense_categories,
        'income_categories': income_categories,
        'expense_transactions': expense_transactions,
        'income_transactions': income_transactions,
        'hierarchical_expense_data_json': json.dumps(stats_data.get('hierarchical_expense_data', [])),
        **stats_data
    }
    return render(request, 'admin/statistics.html', context)


# Add dashboard URL to admin site
original_get_urls = admin.site.get_urls

def custom_get_urls():
    urls = original_get_urls()
    custom_urls = [
        path('dashboard/', admin.site.admin_view(dashboard_view), name='dashboard'),
        path('statistics/', admin.site.admin_view(statistics_view), name='statistics'),
        path('switch-language/', admin.site.admin_view(switch_language), name='switch_language'),
    ]
    return custom_urls + urls

admin.site.get_urls = custom_get_urls 