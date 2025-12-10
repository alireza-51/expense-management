from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.db.models import Sum, Q, Count
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.db.models.functions import TruncDate
from expenses.models import Income, Expense
from categories.models import Category
from drf_spectacular.utils import extend_schema
from analytics.api.v1.base import CalendarFilterMixin, get_calendar_parameters, get_calendar_response_schema, get_all_descendants
from datetime import timedelta
import jdatetime


@extend_schema(
    tags=["Dashboard"],
    parameters=get_calendar_parameters(),
    responses={200: get_calendar_response_schema({
        'total_income': {
            'type': 'number',
            'description': 'Total income amount for the month'
        },
        'total_expense': {
            'type': 'number',
            'description': 'Total expense amount for the month'
        },
        'difference': {
            'type': 'number',
            'description': 'Difference between income and expense (income - expense)'
        },
        'savings_rate': {
            'type': 'number',
            'description': 'Savings rate as percentage: (Income - Expenses) / Income * 100'
        },
        'expense_to_income_ratio': {
            'type': 'number',
            'description': 'Expense-to-income ratio: Expenses / Income'
        },
        'average_daily_spending': {
            'type': 'number',
            'description': 'Average daily spending: Total expenses / days in month'
        },
        'projected_month_end_balance': {
            'type': 'number',
            'description': 'Projected month-end difference (income - expenses) based on current spending rate. This is NOT a cumulative balance, but the projected difference for this month only.'
        },
        'days_elapsed': {
            'type': 'integer',
            'description': 'Number of days elapsed in the current month'
        },
        'days_in_month': {
            'type': 'integer',
            'description': 'Total number of days in the month'
        }
    })}
)
class DashboardOverviewView(APIView, CalendarFilterMixin):
    """
    Get monthly aggregates for income, expense, and their difference.
    Supports both Jalali and Gregorian calendars.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """
        Handle GET request with calendar filtering.
        """
        try:
            # Get and validate calendar type
            calendar_type = self.get_calendar_type(request)
            
            # Get month parameter
            month_param = self.get_month_param(request)
            
            # Get workspace
            workspace = self.get_workspace(request)
            
            # Get date range
            start_datetime, end_datetime = self.get_date_range(calendar_type, month_param)
            
            # Get the actual start_date (date object) for month info
            start_date = start_datetime.date()
            end_date = end_datetime.date()
            
            # Get month information
            month_info = self.get_month_info(start_date, calendar_type)
            
            # Calculate aggregates and financial health metrics
            data = self._calculate_aggregates(workspace, start_datetime, end_datetime, start_date, end_date)
            
            # Build response
            response_data = {
                **month_info,
                'month_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                **data
            }
            
            return Response(response_data)
            
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': _('An unexpected error occurred.'), 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _calculate_aggregates(self, workspace, start_datetime, end_datetime, start_date, end_date):
        """
        Calculate monthly aggregates for income and expense, plus financial health metrics.
        """
        # Filter by workspace and date range
        base_filter = Q(
            workspace=workspace,
            transacted_at__gte=start_datetime,
            transacted_at__lte=end_datetime
        )
        
        # Aggregate income
        total_income = Income.objects.filter(base_filter, category__type=Category.CategoryType.INCOME).aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        # Aggregate expense
        total_expense = Expense.objects.filter(base_filter, category__type=Category.CategoryType.EXPENSE).aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        # Calculate difference
        difference = total_income - total_expense
        
        # Calculate days in month
        days_in_month = (end_date - start_date).days + 1
        
        # Calculate days elapsed (current date relative to month range)
        today = timezone.now().date()
        if today < start_date:
            # If today is before the month start, no days elapsed
            days_elapsed = 0
        elif today > end_date:
            # If today is after the month end, all days elapsed
            days_elapsed = days_in_month
        else:
            # Days elapsed from start of month to today (inclusive)
            days_elapsed = (today - start_date).days + 1
        
        # Calculate financial health metrics
        # Savings rate: (Income - Expenses) / Income * 100
        savings_rate = ((total_income - total_expense) / total_income * 100) if total_income > 0 else 0
        
        # Expense-to-income ratio: Expenses / Income
        expense_to_income_ratio = (total_expense / total_income) if total_income > 0 else 0
        
        # Average daily spending: Total expenses / days in month
        average_daily_spending = total_expense / days_in_month if days_in_month > 0 else 0
        
        # Projected month-end difference: Based on current spending rate
        # This projects what the difference (income - expenses) will be at the end of the month
        # If the month has already ended, use actual difference (no projection needed)
        if today > end_date:
            # Month is in the past, use actual difference
            projected_month_end_balance = difference
        elif days_elapsed > 0 and days_elapsed < days_in_month and total_expense > 0:
            # Month is in progress, project based on current spending rate
            # Only project if we have meaningful data (at least 3 days elapsed for better accuracy)
            # For very early in the month, projections can be unreliable
            if days_elapsed >= 3:
                # Calculate average daily spending so far
                average_daily_spending_so_far = float(total_expense) / days_elapsed
                remaining_days = days_in_month - days_elapsed
                
                # Project remaining expenses based on current spending rate
                projected_remaining_expenses = average_daily_spending_so_far * remaining_days
                projected_total_expenses = float(total_expense) + projected_remaining_expenses
                
                # Projected difference = income - projected expenses
                # Note: We assume income is already complete for the month
                # If income might still come in, this could be adjusted
                projected_month_end_balance = float(total_income) - projected_total_expenses
            else:
                # Too early in the month for reliable projection, use current difference
                # Or provide a conservative estimate based on average daily spending
                if days_in_month > 0:
                    # Use average daily spending across full month as a conservative estimate
                    projected_total_expenses = float(total_expense) * (days_in_month / days_elapsed) if days_elapsed > 0 else float(total_expense)
                    projected_month_end_balance = float(total_income) - projected_total_expenses
                else:
                    projected_month_end_balance = difference
        else:
            # Month hasn't started yet or no expenses, use current difference
            projected_month_end_balance = difference
        
        return {
            'total_income': float(total_income),
            'total_expense': float(total_expense),
            'difference': float(difference),
            'savings_rate': round(float(savings_rate), 2),
            'expense_to_income_ratio': round(float(expense_to_income_ratio), 4),
            'average_daily_spending': round(float(average_daily_spending), 2),
            'projected_month_end_balance': round(float(projected_month_end_balance), 2),
            'days_elapsed': days_elapsed,
            'days_in_month': days_in_month,
        }


@extend_schema(
    tags=["Dashboard"],
    parameters=get_calendar_parameters(),
    responses={200: get_calendar_response_schema({
        'data': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'id': {'type': 'integer', 'description': 'Category ID'},
                    'name': {'type': 'string', 'description': 'Category name'},
                    'amount': {'type': 'number', 'description': 'Total amount (including children)'},
                    'color': {'type': 'string', 'description': 'Category color'},
                    'percentage': {'type': 'number', 'description': 'Percentage of total'}
                }
            },
            'description': 'Pie chart data for income distribution by main categories'
        }
    })}
)
class IncomeDistributionView(APIView, CalendarFilterMixin):
    """
    Get income distribution across main categories (categories with no parent).
    Sums amounts from the main category and all its children for pie chart visualization.
    Supports both Jalali and Gregorian calendars.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """
        Handle GET request with calendar filtering.
        """
        try:
            # Get and validate calendar type
            calendar_type = self.get_calendar_type(request)
            
            # Get month parameter
            month_param = self.get_month_param(request)
            
            # Get workspace
            workspace = self.get_workspace(request)
            
            # Get date range
            start_datetime, end_datetime = self.get_date_range(calendar_type, month_param)
            
            # Get the actual start_date (date object) for month info
            start_date = start_datetime.date()
            end_date = end_datetime.date()
            
            # Get month information
            month_info = self.get_month_info(start_date, calendar_type)
            
            # Calculate distribution
            data = self._calculate_distribution(workspace, start_datetime, end_datetime)
            
            # Build response
            response_data = {
                **month_info,
                'month_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'data': data
            }
            
            return Response(response_data)
            
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': _('An unexpected error occurred.'), 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _calculate_distribution(self, workspace, start_datetime, end_datetime):
        """
        Calculate income distribution across main categories.
        """
        # Get all main categories (no parent) of type INCOME
        main_categories = Category.objects.filter(
            parent__isnull=True,
            type=Category.CategoryType.INCOME
        )
        
        pie_data = []
        
        for main_category in main_categories:
            # Get all descendants including the main category itself
            all_categories = get_all_descendants(main_category)
            category_ids = [cat.id for cat in all_categories]
            
            # Sum all income transactions for this category and all its descendants
            total_amount = Income.objects.filter(
                workspace=workspace,
                transacted_at__gte=start_datetime,
                transacted_at__lte=end_datetime,
                category__id__in=category_ids,
                category__type=Category.CategoryType.INCOME
            ).aggregate(
                total=Sum('amount')
            )['total'] or 0
            
            # Only include categories with transactions
            if total_amount > 0:
                pie_data.append({
                    'id': main_category.id,
                    'name': main_category.name,
                    'amount': float(total_amount),
                    'color': main_category.color,
                    'percentage': 0  # Will be calculated below
                })
        
        # Calculate percentages
        total_amount = sum(item['amount'] for item in pie_data)
        for item in pie_data:
            item['percentage'] = (item['amount'] / total_amount * 100) if total_amount > 0 else 0
        
        # Sort by amount descending
        pie_data.sort(key=lambda x: x['amount'], reverse=True)
        
        return pie_data


@extend_schema(
    tags=["Dashboard"],
    parameters=get_calendar_parameters(),
    responses={200: get_calendar_response_schema({
        'data': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'id': {'type': 'integer', 'description': 'Category ID'},
                    'name': {'type': 'string', 'description': 'Category name'},
                    'amount': {'type': 'number', 'description': 'Total amount (including children)'},
                    'color': {'type': 'string', 'description': 'Category color'},
                    'percentage': {'type': 'number', 'description': 'Percentage of total'}
                }
            },
            'description': 'Pie chart data for expense distribution by main categories'
        }
    })}
)
class ExpenseDistributionView(APIView, CalendarFilterMixin):
    """
    Get expense distribution across main categories (categories with no parent).
    Sums amounts from the main category and all its children for pie chart visualization.
    Supports both Jalali and Gregorian calendars.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """
        Handle GET request with calendar filtering.
        """
        try:
            # Get and validate calendar type
            calendar_type = self.get_calendar_type(request)
            
            # Get month parameter
            month_param = self.get_month_param(request)
            
            # Get workspace
            workspace = self.get_workspace(request)
            
            # Get date range
            start_datetime, end_datetime = self.get_date_range(calendar_type, month_param)
            
            # Get the actual start_date (date object) for month info
            start_date = start_datetime.date()
            end_date = end_datetime.date()
            
            # Get month information
            month_info = self.get_month_info(start_date, calendar_type)
            
            # Calculate distribution
            data = self._calculate_distribution(workspace, start_datetime, end_datetime)
            
            # Build response
            response_data = {
                **month_info,
                'month_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'data': data
            }
            
            return Response(response_data)
            
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': _('An unexpected error occurred.'), 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _calculate_distribution(self, workspace, start_datetime, end_datetime):
        """
        Calculate expense distribution across main categories.
        """
        # Get all main categories (no parent) of type EXPENSE
        main_categories = Category.objects.filter(
            parent__isnull=True,
            type=Category.CategoryType.EXPENSE
        )
        
        pie_data = []
        
        for main_category in main_categories:
            # Get all descendants including the main category itself
            all_categories = get_all_descendants(main_category)
            category_ids = [cat.id for cat in all_categories]
            
            # Sum all expense transactions for this category and all its descendants
            total_amount = Expense.objects.filter(
                workspace=workspace,
                transacted_at__gte=start_datetime,
                transacted_at__lte=end_datetime,
                category__id__in=category_ids,
                category__type=Category.CategoryType.EXPENSE
            ).aggregate(
                total=Sum('amount')
            )['total'] or 0
            
            # Only include categories with transactions
            if total_amount > 0:
                pie_data.append({
                    'id': main_category.id,
                    'name': main_category.name,
                    'amount': float(total_amount),
                    'color': main_category.color,
                    'percentage': 0  # Will be calculated below
                })
        
        # Calculate percentages
        total_amount = sum(item['amount'] for item in pie_data)
        for item in pie_data:
            item['percentage'] = (item['amount'] / total_amount * 100) if total_amount > 0 else 0
        
        # Sort by amount descending
        pie_data.sort(key=lambda x: x['amount'], reverse=True)
        
        return pie_data


@extend_schema(
    tags=["Dashboard"],
    parameters=get_calendar_parameters(),
    responses={200: get_calendar_response_schema({
        'chart_data': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'date': {'type': 'string', 'format': 'date', 'description': 'Date in YYYY-MM-DD format (Gregorian)'},
                    'date_display': {'type': 'string', 'description': 'Formatted date string in the requested calendar format'},
                    'day': {'type': 'integer', 'description': 'Day number in the month (1-31)'},
                    'day_name': {'type': 'string', 'description': 'Day of week name'},
                    'day_of_week': {'type': 'integer', 'description': 'Day of week (0=Monday, 6=Sunday)'},
                    'income': {'type': 'number', 'description': 'Total income amount for this day'},
                    'expense': {'type': 'number', 'description': 'Total expense amount for this day'},
                    'net': {'type': 'number', 'description': 'Net amount (income - expense) for this day'},
                    'cumulative_income': {'type': 'number', 'description': 'Cumulative income from start of month'},
                    'cumulative_expense': {'type': 'number', 'description': 'Cumulative expense from start of month'},
                    'cumulative_net': {'type': 'number', 'description': 'Cumulative net from start of month'},
                    'income_percentage': {'type': 'number', 'description': 'Percentage of monthly income on this day'},
                    'expense_percentage': {'type': 'number', 'description': 'Percentage of monthly expense on this day'},
                    'income_count': {'type': 'integer', 'description': 'Number of income transactions'},
                    'expense_count': {'type': 'integer', 'description': 'Number of expense transactions'}
                }
            },
            'description': 'Daily income and expense data distribution for the month'
        },
        'summary': {
            'type': 'object',
            'properties': {
                'total_income': {'type': 'number', 'description': 'Total income for the month'},
                'total_expense': {'type': 'number', 'description': 'Total expense for the month'},
                'net_amount': {'type': 'number', 'description': 'Net amount (income - expense) for the month'},
                'average_daily_income': {'type': 'number', 'description': 'Average daily income'},
                'average_daily_expense': {'type': 'number', 'description': 'Average daily expense'},
                'days_with_income': {'type': 'integer', 'description': 'Number of days with income transactions'},
                'days_with_expense': {'type': 'integer', 'description': 'Number of days with expense transactions'},
                'peak_income_day': {'type': 'object', 'description': 'Day with highest income'},
                'peak_expense_day': {'type': 'object', 'description': 'Day with highest expense'}
            }
        }
    })}
)
class MonthlyChartView(APIView, CalendarFilterMixin):
    """
    Get monthly expense and income chart data showing daily distribution.
    Returns detailed daily data for line/bar chart visualization with cumulative totals,
    percentages, and distribution metrics.
    Supports both Jalali and Gregorian calendars.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """
        Handle GET request with calendar filtering.
        """
        try:
            # Get and validate calendar type
            calendar_type = self.get_calendar_type(request)
            
            # Get month parameter
            month_param = self.get_month_param(request)
            
            # Get workspace
            workspace = self.get_workspace(request)
            
            # Get date range
            start_datetime, end_datetime = self.get_date_range(calendar_type, month_param)
            start_date = start_datetime.date()
            end_date = end_datetime.date()
            
            # Get month information
            month_info = self.get_month_info(start_date, calendar_type)
            
            # Calculate chart data
            chart_data, summary = self._calculate_monthly_chart(
                workspace, start_datetime, end_datetime, start_date, end_date, calendar_type
            )
            
            # Build response
            response_data = {
                **month_info,
                'month_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'chart_data': chart_data,
                'summary': summary
            }
            
            return Response(response_data)
            
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': _('An unexpected error occurred.'), 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _calculate_monthly_chart(self, workspace, start_datetime, end_datetime, start_date, end_date, calendar_type):
        """Calculate daily income and expense data for the month with distribution metrics."""
        # Get daily income aggregates
        daily_income = Income.objects.filter(
            workspace=workspace,
            transacted_at__gte=start_datetime,
            transacted_at__lte=end_datetime,
            category__type=Category.CategoryType.INCOME
        ).annotate(
            date=TruncDate('transacted_at')
        ).values('date').annotate(
            amount=Sum('amount'),
            count=Count('id')
        ).order_by('date')
        
        # Get daily expense aggregates
        daily_expense = Expense.objects.filter(
            workspace=workspace,
            transacted_at__gte=start_datetime,
            transacted_at__lte=end_datetime,
            category__type=Category.CategoryType.EXPENSE
        ).annotate(
            date=TruncDate('transacted_at')
        ).values('date').annotate(
            amount=Sum('amount'),
            count=Count('id')
        ).order_by('date')
        
        # Convert to dicts for easy lookup
        income_by_date = {
            item['date']: {
                'amount': float(item['amount'] or 0),
                'count': item['count'] or 0
            }
            for item in daily_income
        }
        expense_by_date = {
            item['date']: {
                'amount': float(item['amount'] or 0),
                'count': item['count'] or 0
            }
            for item in daily_expense
        }
        
        # Day names for both calendars (0=Monday, 1=Tuesday, ..., 6=Sunday)
        gregorian_day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        jalali_day_names_fa = ['دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنج‌شنبه', 'جمعه', 'شنبه', 'یکشنبه']  # Mon-Sun
        jalali_day_names_en = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        # Get current language
        from django.utils.translation import get_language
        current_language = get_language() or 'en'
        
        # Generate chart data for all dates in the month
        current_date = start_date
        chart_data = []
        total_income = 0.0
        total_expense = 0.0
        days_with_income = 0
        days_with_expense = 0
        cumulative_income = 0.0
        cumulative_expense = 0.0
        
        # Track peak days
        peak_income_day = None
        peak_expense_day = None
        max_income = 0.0
        max_expense = 0.0
        
        while current_date <= end_date:
            income_data = income_by_date.get(current_date, {'amount': 0.0, 'count': 0})
            expense_data = expense_by_date.get(current_date, {'amount': 0.0, 'count': 0})
            
            income_amount = income_data['amount']
            expense_amount = expense_data['amount']
            net_amount = income_amount - expense_amount
            
            # Update cumulative totals
            cumulative_income += income_amount
            cumulative_expense += expense_amount
            cumulative_net = cumulative_income - cumulative_expense
            
            total_income += income_amount
            total_expense += expense_amount
            
            # Track peak days
            if income_amount > max_income:
                max_income = income_amount
                peak_income_day = {
                    'date': current_date.isoformat(),
                    'amount': round(income_amount, 2),
                    'day': current_date.day
                }
            
            if expense_amount > max_expense:
                max_expense = expense_amount
                peak_expense_day = {
                    'date': current_date.isoformat(),
                    'amount': round(expense_amount, 2),
                    'day': current_date.day
                }
            
            if income_amount > 0:
                days_with_income += 1
            if expense_amount > 0:
                days_with_expense += 1
            
            # Format date display based on calendar type
            if calendar_type == 'jalali':
                jalali_date = jdatetime.date.fromgregorian(date=current_date)
                date_display = jalali_date.strftime('%Y/%m/%d')
                day_number = jalali_date.day
                # jdatetime.weekday() returns 0=Saturday, 1=Sunday, ..., 6=Friday
                # Convert to standard 0=Monday, 1=Tuesday, ..., 6=Sunday
                jalali_weekday = jalali_date.weekday()
                # Map: Sat(0)->5, Sun(1)->6, Mon(2)->0, Tue(3)->1, Wed(4)->2, Thu(5)->3, Fri(6)->4
                day_of_week = (jalali_weekday + 5) % 7
                if current_language == 'fa':
                    day_name = jalali_day_names_fa[day_of_week]
                else:
                    day_name = jalali_day_names_en[day_of_week]
            else:
                date_display = current_date.strftime('%Y-%m-%d')
                day_number = current_date.day
                day_of_week = current_date.weekday()  # 0=Monday, 6=Sunday
                day_name = gregorian_day_names[day_of_week]
            
            # Calculate percentages (will be calculated after we know totals)
            chart_data.append({
                'date': current_date.isoformat(),
                'date_display': date_display,
                'day': day_number,
                'day_name': day_name,
                'day_of_week': day_of_week,
                'income': round(income_amount, 2),
                'expense': round(expense_amount, 2),
                'net': round(net_amount, 2),
                'cumulative_income': round(cumulative_income, 2),
                'cumulative_expense': round(cumulative_expense, 2),
                'cumulative_net': round(cumulative_net, 2),
                'income_count': income_data['count'],
                'expense_count': expense_data['count'],
                'income_percentage': 0.0,  # Will be calculated below
                'expense_percentage': 0.0  # Will be calculated below
            })
            
            current_date += timedelta(days=1)
        
        # Calculate percentages for each day
        for day_data in chart_data:
            if total_income > 0:
                day_data['income_percentage'] = round((day_data['income'] / total_income) * 100, 2)
            if total_expense > 0:
                day_data['expense_percentage'] = round((day_data['expense'] / total_expense) * 100, 2)
        
        # Calculate summary statistics
        days_in_month = len(chart_data)
        average_daily_income = total_income / days_in_month if days_in_month > 0 else 0
        average_daily_expense = total_expense / days_in_month if days_in_month > 0 else 0
        
        summary = {
            'total_income': round(total_income, 2),
            'total_expense': round(total_expense, 2),
            'net_amount': round(total_income - total_expense, 2),
            'average_daily_income': round(average_daily_income, 2),
            'average_daily_expense': round(average_daily_expense, 2),
            'days_with_income': days_with_income,
            'days_with_expense': days_with_expense,
            'peak_income_day': peak_income_day,
            'peak_expense_day': peak_expense_day
        }
        
        return chart_data, summary

