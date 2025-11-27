from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.db.models import Sum
from expenses.models import Income, Expense
from categories.models import Category
from drf_spectacular.utils import extend_schema
from analytics.api.v1.base import CalendarFilterMixin, get_calendar_parameters, get_calendar_response_schema
from datetime import timedelta
from django.db.models.functions import TruncDate

@extend_schema(
    tags=["Cash Flow"],
    parameters=get_calendar_parameters(),
    responses={200: get_calendar_response_schema({
        'timeline': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'date': {'type': 'string', 'format': 'date', 'description': 'Date in YYYY-MM-DD format'},
                    'cumulative_balance': {'type': 'number', 'description': 'Cumulative balance up to this date'},
                    'daily_income': {'type': 'number', 'description': 'Income on this date'},
                    'daily_expense': {'type': 'number', 'description': 'Expense on this date'},
                    'daily_net': {'type': 'number', 'description': 'Net change (income - expense) on this date'}
                }
            },
            'description': 'Cash flow timeline data'
        },
        'summary': {
            'type': 'object',
            'properties': {
                'starting_balance': {'type': 'number', 'description': 'Balance at start of month (assumed 0 or from previous month)'},
                'ending_balance': {'type': 'number', 'description': 'Balance at end of month'},
                'total_income': {'type': 'number'},
                'total_expenses': {'type': 'number'},
                'net_change': {'type': 'number'}
            }
        }
    })}
)
class CashFlowTimelineView(APIView, CalendarFilterMixin):
    """
    Get cash flow timeline showing cumulative balance throughout the month.
    Line chart data showing how balance changes over time.
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
            
            # Calculate cash flow timeline
            timeline_data, summary = self._calculate_cash_flow_timeline(workspace, start_datetime, end_datetime)
            
            # Build response
            response_data = {
                **month_info,
                'month_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'timeline': timeline_data,
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
                {'error': 'An unexpected error occurred.', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _calculate_cash_flow_timeline(self, workspace, start_datetime, end_datetime):
        """Calculate cash flow timeline with cumulative balance."""
        # Get daily income and expense aggregates
        daily_income = Income.objects.filter(
            workspace=workspace,
            transacted_at__gte=start_datetime,
            transacted_at__lte=end_datetime,
            category__type=Category.CategoryType.INCOME
        ).annotate(
            date=TruncDate('transacted_at')
        ).values('date').annotate(
            amount=Sum('amount')
        ).order_by('date')
        
        daily_expense = Expense.objects.filter(
            workspace=workspace,
            transacted_at__gte=start_datetime,
            transacted_at__lte=end_datetime,
            category__type=Category.CategoryType.EXPENSE
        ).annotate(
            date=TruncDate('transacted_at')
        ).values('date').annotate(
            amount=Sum('amount')
        ).order_by('date')
        
        # Convert to dicts for easy lookup
        income_by_date = {item['date']: float(item['amount'] or 0) for item in daily_income}
        expense_by_date = {item['date']: float(item['amount'] or 0) for item in daily_expense}
        
        # Generate timeline for all dates in range
        current_date = start_datetime.date()
        end_date = end_datetime.date()
        timeline = []
        cumulative_balance = 0.0
        total_income = 0.0
        total_expenses = 0.0
        
        while current_date <= end_date:
            daily_income_amount = income_by_date.get(current_date, 0.0)
            daily_expense_amount = expense_by_date.get(current_date, 0.0)
            daily_net = daily_income_amount - daily_expense_amount
            
            cumulative_balance += daily_net
            total_income += daily_income_amount
            total_expenses += daily_expense_amount
            
            timeline.append({
                'date': current_date.isoformat(),
                'cumulative_balance': round(cumulative_balance, 2),
                'daily_income': round(daily_income_amount, 2),
                'daily_expense': round(daily_expense_amount, 2),
                'daily_net': round(daily_net, 2)
            })
            
            current_date += timedelta(days=1)
        
        # Calculate summary
        starting_balance = 0.0  # Could be enhanced to get from previous month
        ending_balance = cumulative_balance
        net_change = total_income - total_expenses
        
        summary = {
            'starting_balance': round(starting_balance, 2),
            'ending_balance': round(ending_balance, 2),
            'total_income': round(total_income, 2),
            'total_expenses': round(total_expenses, 2),
            'net_change': round(net_change, 2)
        }
        
        return timeline, summary


@extend_schema(
    tags=["Cash Flow"],
    parameters=get_calendar_parameters(),
    responses={200: get_calendar_response_schema({
        'timeline': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'date': {'type': 'string', 'format': 'date', 'description': 'Date in YYYY-MM-DD format'},
                    'income': {'type': 'number', 'description': 'Income amount on this date'},
                    'expense': {'type': 'number', 'description': 'Expense amount on this date'},
                    'cumulative_income': {'type': 'number', 'description': 'Cumulative income up to this date'},
                    'cumulative_expense': {'type': 'number', 'description': 'Cumulative expense up to this date'}
                }
            },
            'description': 'Income vs Expense timeline data for overlapping lines'
        },
        'summary': {
            'type': 'object',
            'properties': {
                'total_income': {'type': 'number'},
                'total_expenses': {'type': 'number'},
                'net_flow': {'type': 'number', 'description': 'Net cash flow (income - expenses)'}
            }
        }
    })}
)
class IncomeVsExpenseTimelineView(APIView, CalendarFilterMixin):
    """
    Get income vs expense timeline with overlapping lines.
    Shows when money comes in vs goes out throughout the month.
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
            
            # Calculate income vs expense timeline
            timeline_data, summary = self._calculate_income_vs_expense_timeline(workspace, start_datetime, end_datetime)
            
            # Build response
            response_data = {
                **month_info,
                'month_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'timeline': timeline_data,
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
                {'error': 'An unexpected error occurred.', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _calculate_income_vs_expense_timeline(self, workspace, start_datetime, end_datetime):
        """Calculate income vs expense timeline."""
        # Get daily income and expense aggregates
        daily_income = Income.objects.filter(
            workspace=workspace,
            transacted_at__gte=start_datetime,
            transacted_at__lte=end_datetime,
            category__type=Category.CategoryType.INCOME
        ).annotate(
            date=TruncDate('transacted_at')
        ).values('date').annotate(
            amount=Sum('amount')
        ).order_by('date')
        
        daily_expense = Expense.objects.filter(
            workspace=workspace,
            transacted_at__gte=start_datetime,
            transacted_at__lte=end_datetime,
            category__type=Category.CategoryType.EXPENSE
        ).annotate(
            date=TruncDate('transacted_at')
        ).values('date').annotate(
            amount=Sum('amount')
        ).order_by('date')
        
        # Convert to dicts for easy lookup
        income_by_date = {item['date']: float(item['amount'] or 0) for item in daily_income}
        expense_by_date = {item['date']: float(item['amount'] or 0) for item in daily_expense}
        
        # Generate timeline for all dates in range
        current_date = start_datetime.date()
        end_date = end_datetime.date()
        timeline = []
        cumulative_income = 0.0
        cumulative_expense = 0.0
        total_income = 0.0
        total_expenses = 0.0
        
        while current_date <= end_date:
            daily_income_amount = income_by_date.get(current_date, 0.0)
            daily_expense_amount = expense_by_date.get(current_date, 0.0)
            
            cumulative_income += daily_income_amount
            cumulative_expense += daily_expense_amount
            total_income += daily_income_amount
            total_expenses += daily_expense_amount
            
            timeline.append({
                'date': current_date.isoformat(),
                'income': round(daily_income_amount, 2),
                'expense': round(daily_expense_amount, 2),
                'cumulative_income': round(cumulative_income, 2),
                'cumulative_expense': round(cumulative_expense, 2)
            })
            
            current_date += timedelta(days=1)
        
        # Calculate summary
        net_flow = total_income - total_expenses
        
        summary = {
            'total_income': round(total_income, 2),
            'total_expenses': round(total_expenses, 2),
            'net_flow': round(net_flow, 2)
        }
        
        return timeline, summary


@extend_schema(
    tags=["Cash Flow"],
    parameters=get_calendar_parameters(),
    responses={200: get_calendar_response_schema({
        'balance_trend': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'date': {'type': 'string', 'format': 'date', 'description': 'Date in YYYY-MM-DD format'},
                    'balance': {'type': 'number', 'description': 'Balance at end of this day'},
                    'change': {'type': 'number', 'description': 'Change in balance from previous day'},
                    'change_percentage': {'type': 'number', 'description': 'Percentage change from previous day'}
                }
            },
            'description': 'Day-by-day balance trend'
        },
        'summary': {
            'type': 'object',
            'properties': {
                'starting_balance': {'type': 'number'},
                'ending_balance': {'type': 'number'},
                'highest_balance': {'type': 'number'},
                'lowest_balance': {'type': 'number'},
                'average_balance': {'type': 'number'},
                'total_change': {'type': 'number'}
            }
        }
    })}
)
class BalanceTrendView(APIView, CalendarFilterMixin):
    """
    Get balance trend showing how the balance changes day-by-day.
    Line chart data for balance progression throughout the month.
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
            
            # Calculate balance trend
            trend_data, summary = self._calculate_balance_trend(workspace, start_datetime, end_datetime)
            
            # Build response
            response_data = {
                **month_info,
                'month_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'balance_trend': trend_data,
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
                {'error': 'An unexpected error occurred.', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _calculate_balance_trend(self, workspace, start_datetime, end_datetime):
        """Calculate day-by-day balance trend."""
        # Get daily income and expense aggregates
        daily_income = Income.objects.filter(
            workspace=workspace,
            transacted_at__gte=start_datetime,
            transacted_at__lte=end_datetime,
            category__type=Category.CategoryType.INCOME
        ).annotate(
            date=TruncDate('transacted_at')
        ).values('date').annotate(
            amount=Sum('amount')
        ).order_by('date')
        
        daily_expense = Expense.objects.filter(
            workspace=workspace,
            transacted_at__gte=start_datetime,
            transacted_at__lte=end_datetime,
            category__type=Category.CategoryType.EXPENSE
        ).annotate(
            date=TruncDate('transacted_at')
        ).values('date').annotate(
            amount=Sum('amount')
        ).order_by('date')
        
        # Convert to dicts for easy lookup
        income_by_date = {item['date']: float(item['amount'] or 0) for item in daily_income}
        expense_by_date = {item['date']: float(item['amount'] or 0) for item in daily_expense}
        
        # Generate balance trend for all dates in range
        current_date = start_datetime.date()
        end_date = end_datetime.date()
        balance_trend = []
        balance = 0.0  # Starting balance (could be enhanced to get from previous month)
        previous_balance = balance
        balances = []
        
        while current_date <= end_date:
            daily_income_amount = income_by_date.get(current_date, 0.0)
            daily_expense_amount = expense_by_date.get(current_date, 0.0)
            daily_change = daily_income_amount - daily_expense_amount
            
            balance += daily_change
            balances.append(balance)
            
            # Calculate percentage change
            if previous_balance != 0:
                change_percentage = ((balance - previous_balance) / abs(previous_balance)) * 100
            else:
                change_percentage = 100.0 if balance > 0 else 0.0
            
            balance_trend.append({
                'date': current_date.isoformat(),
                'balance': round(balance, 2),
                'change': round(daily_change, 2),
                'change_percentage': round(change_percentage, 2)
            })
            
            previous_balance = balance
            current_date += timedelta(days=1)
        
        # Calculate summary
        starting_balance = balance_trend[0]['balance'] if balance_trend else 0.0
        ending_balance = balance_trend[-1]['balance'] if balance_trend else 0.0
        highest_balance = max(balances) if balances else 0.0
        lowest_balance = min(balances) if balances else 0.0
        average_balance = sum(balances) / len(balances) if balances else 0.0
        total_change = ending_balance - starting_balance
        
        summary = {
            'starting_balance': round(starting_balance, 2),
            'ending_balance': round(ending_balance, 2),
            'highest_balance': round(highest_balance, 2),
            'lowest_balance': round(lowest_balance, 2),
            'average_balance': round(average_balance, 2),
            'total_change': round(total_change, 2)
        }
        
        return balance_trend, summary
