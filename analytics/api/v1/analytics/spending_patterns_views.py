from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.db.models import Sum, Q, Count
from django.utils.translation import gettext_lazy as _
from expenses.models import Expense
from categories.models import Category
from drf_spectacular.utils import extend_schema, OpenApiParameter
from analytics.api.v1.base import CalendarFilterMixin, get_calendar_parameters, get_calendar_response_schema
from datetime import timedelta
from django.db.models.functions import Extract, TruncDate

@extend_schema(
    tags=["Spending Patterns"],
    parameters=get_calendar_parameters(),
    responses={200: get_calendar_response_schema({
        'heatmap_data': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'date': {'type': 'string', 'format': 'date', 'description': 'Date in YYYY-MM-DD format'},
                    'amount': {'type': 'number', 'description': 'Total spending for the day'},
                    'transaction_count': {'type': 'integer', 'description': 'Number of transactions on this day'},
                    'intensity': {
                        'type': 'string',
                        'enum': ['none', 'low', 'medium', 'high', 'very_high'],
                        'description': 'Spending intensity level for visualization'
                    }
                }
            },
            'description': 'Daily spending data for calendar heatmap'
        },
        'summary': {
            'type': 'object',
            'properties': {
                'total_days': {'type': 'integer'},
                'days_with_spending': {'type': 'integer'},
                'average_daily_spending': {'type': 'number'},
                'max_daily_spending': {'type': 'number'},
                'min_daily_spending': {'type': 'number'}
            }
        }
    })}
)
class DailySpendingHeatmapView(APIView, CalendarFilterMixin):
    """
    Get daily spending heatmap data for calendar view.
    Shows spending intensity per day with color coding.
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
            
            # Calculate heatmap data
            heatmap_data, summary = self._calculate_heatmap(workspace, start_datetime, end_datetime)
            
            # Build response
            response_data = {
                **month_info,
                'month_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'heatmap_data': heatmap_data,
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
    
    def _calculate_heatmap(self, workspace, start_datetime, end_datetime):
        """Calculate daily spending heatmap data."""
        # Get daily spending aggregates
        daily_data = Expense.objects.filter(
            workspace=workspace,
            transacted_at__gte=start_datetime,
            transacted_at__lte=end_datetime,
            category__type=Category.CategoryType.EXPENSE
        ).annotate(
            date=TruncDate('transacted_at')
        ).values('date').annotate(
            amount=Sum('amount'),
            transaction_count=Count('id')
        ).order_by('date')
        
        # Convert to dict for easy lookup
        spending_by_date = {item['date']: item for item in daily_data}
        
        # Generate all dates in the range
        current_date = start_datetime.date()
        end_date = end_datetime.date()
        heatmap_data = []
        amounts = []
        
        while current_date <= end_date:
            date_data = spending_by_date.get(current_date, {
                'amount': 0,
                'transaction_count': 0
            })
            
            amount = float(date_data['amount'] or 0)
            amounts.append(amount)
            
            heatmap_data.append({
                'date': current_date.isoformat(),
                'amount': amount,
                'transaction_count': date_data['transaction_count'],
                'intensity': self._calculate_intensity(amount, amounts)
            })
            
            current_date += timedelta(days=1)
        
        # Calculate summary
        days_with_spending = sum(1 for item in heatmap_data if item['amount'] > 0)
        total_days = len(heatmap_data)
        total_amount = sum(item['amount'] for item in heatmap_data)
        max_amount = max(item['amount'] for item in heatmap_data) if amounts else 0
        min_amount = min(item['amount'] for item in heatmap_data if item['amount'] > 0) if any(item['amount'] > 0 for item in heatmap_data) else 0
        
        summary = {
            'total_days': total_days,
            'days_with_spending': days_with_spending,
            'average_daily_spending': round(total_amount / total_days, 2) if total_days > 0 else 0,
            'max_daily_spending': round(max_amount, 2),
            'min_daily_spending': round(min_amount, 2)
        }
        
        return heatmap_data, summary
    
    def _calculate_intensity(self, amount, all_amounts):
        """Calculate spending intensity level."""
        if amount == 0:
            return 'none'
        
        # Calculate percentiles for intensity levels
        if not all_amounts or all(a == 0 for a in all_amounts):
            return 'low'
        
        non_zero_amounts = [a for a in all_amounts if a > 0]
        if not non_zero_amounts:
            return 'low'
        
        sorted_amounts = sorted(non_zero_amounts)
        max_amount = sorted_amounts[-1]
        
        if max_amount == 0:
            return 'low'
        
        percentage = (amount / max_amount) * 100
        
        if percentage >= 80:
            return 'very_high'
        elif percentage >= 60:
            return 'high'
        elif percentage >= 30:
            return 'medium'
        else:
            return 'low'


@extend_schema(
    tags=["Spending Patterns"],
    parameters=get_calendar_parameters(),
    responses={200: get_calendar_response_schema({
        'weekly_breakdown': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'day_of_week': {'type': 'integer', 'description': '0=Monday, 6=Sunday'},
                    'day_name': {'type': 'string', 'description': 'Day name (Monday, Tuesday, etc.)'},
                    'amount': {'type': 'number', 'description': 'Total spending for this day of week'},
                    'transaction_count': {'type': 'integer', 'description': 'Number of transactions'},
                    'average_per_day': {'type': 'number', 'description': 'Average spending per occurrence of this day'}
                }
            },
            'description': 'Spending breakdown by day of week'
        },
        'summary': {
            'type': 'object',
            'properties': {
                'busiest_day': {'type': 'string', 'description': 'Day with highest spending'},
                'quietest_day': {'type': 'string', 'description': 'Day with lowest spending'},
                'total_weekly_spending': {'type': 'number'}
            }
        }
    })}
)
class WeeklyBreakdownView(APIView, CalendarFilterMixin):
    """
    Get weekly breakdown of spending by day of week.
    Shows bar chart data for spending patterns across weekdays.
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
            
            # Calculate weekly breakdown
            weekly_data, summary = self._calculate_weekly_breakdown(workspace, start_datetime, end_datetime)
            
            # Build response
            response_data = {
                **month_info,
                'month_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'weekly_breakdown': weekly_data,
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
    
    def _calculate_weekly_breakdown(self, workspace, start_datetime, end_datetime):
        """Calculate weekly breakdown by day of week."""
        # Get spending by day of week (0=Monday, 6=Sunday)
        daily_data = Expense.objects.filter(
            workspace=workspace,
            transacted_at__gte=start_datetime,
            transacted_at__lte=end_datetime,
            category__type=Category.CategoryType.EXPENSE
        ).annotate(
            day_of_week=Extract('transacted_at', 'dow')  # PostgreSQL day of week (0=Sunday, 6=Saturday)
        ).values('day_of_week').annotate(
            amount=Sum('amount'),
            transaction_count=Count('id'),
            day_count=Count('transacted_at__date', distinct=True)
        ).order_by('day_of_week')
        
        # Day names mapping (PostgreSQL: 0=Sunday, 1=Monday, ..., 6=Saturday)
        # Convert to standard: 0=Monday, 6=Sunday
        day_names = [
            _('Monday'), _('Tuesday'), _('Wednesday'), _('Thursday'),
            _('Friday'), _('Saturday'), _('Sunday')
        ]
        
        weekly_data = []
        day_totals = {}
        
        for item in daily_data:
            # PostgreSQL returns 0-6 where 0=Sunday, so convert to 0=Monday
            pg_dow = item['day_of_week']
            standard_dow = (pg_dow + 6) % 7  # Convert: 0=Sunday -> 6, 1=Monday -> 0, etc.
            
            amount = float(item['amount'] or 0)
            day_count = item['day_count'] or 1
            
            weekly_data.append({
                'day_of_week': standard_dow,
                'day_name': day_names[standard_dow],
                'amount': amount,
                'transaction_count': item['transaction_count'],
                'average_per_day': round(amount / day_count, 2) if day_count > 0 else 0
            })
            
            day_totals[standard_dow] = amount
        
        # Fill in missing days with zero
        for dow in range(7):
            if dow not in [item['day_of_week'] for item in weekly_data]:
                weekly_data.append({
                    'day_of_week': dow,
                    'day_name': day_names[dow],
                    'amount': 0.0,
                    'transaction_count': 0,
                    'average_per_day': 0.0
                })
        
        # Sort by day of week (Monday first)
        weekly_data.sort(key=lambda x: x['day_of_week'])
        
        # Calculate summary
        if day_totals:
            busiest_day_dow = max(day_totals, key=day_totals.get)
            quietest_day_dow = min(day_totals, key=day_totals.get)
            busiest_day = day_names[busiest_day_dow]
            quietest_day = day_names[quietest_day_dow]
        else:
            busiest_day = None
            quietest_day = None
        
        summary = {
            'busiest_day': busiest_day,
            'quietest_day': quietest_day,
            'total_weekly_spending': round(sum(item['amount'] for item in weekly_data), 2)
        }
        
        return weekly_data, summary


@extend_schema(
    tags=["Spending Patterns"],
    parameters=get_calendar_parameters(),
    responses={200: get_calendar_response_schema({
        'time_breakdown': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'hour': {'type': 'integer', 'description': 'Hour of day (0-23)'},
                    'hour_label': {'type': 'string', 'description': 'Formatted hour label (e.g., "09:00-10:00")'},
                    'amount': {'type': 'number', 'description': 'Total spending in this hour'},
                    'transaction_count': {'type': 'integer', 'description': 'Number of transactions'},
                    'percentage': {'type': 'number', 'description': 'Percentage of total daily spending'}
                }
            },
            'description': 'Spending breakdown by hour of day'
        },
        'summary': {
            'type': 'object',
            'properties': {
                'peak_hour': {'type': 'integer', 'description': 'Hour with highest spending (0-23)'},
                'quietest_hour': {'type': 'integer', 'description': 'Hour with lowest spending (0-23)'},
                'total_spending': {'type': 'number'},
                'average_per_hour': {'type': 'number'}
            }
        }
    })}
)
class TimeBasedAnalysisView(APIView, CalendarFilterMixin):
    """
    Get time-based analysis of spending by hour of day.
    Shows when spending occurs throughout the day.
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
            
            # Calculate time-based breakdown
            time_data, summary = self._calculate_time_breakdown(workspace, start_datetime, end_datetime)
            
            # Build response
            response_data = {
                **month_info,
                'month_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'time_breakdown': time_data,
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
    
    def _calculate_time_breakdown(self, workspace, start_datetime, end_datetime):
        """Calculate spending breakdown by hour of day."""
        # Get spending by hour
        hourly_data = Expense.objects.filter(
            workspace=workspace,
            transacted_at__gte=start_datetime,
            transacted_at__lte=end_datetime,
            category__type=Category.CategoryType.EXPENSE
        ).annotate(
            hour=Extract('transacted_at', 'hour')
        ).values('hour').annotate(
            amount=Sum('amount'),
            transaction_count=Count('id')
        ).order_by('hour')
        
        # Convert to dict for easy lookup
        spending_by_hour = {item['hour']: item for item in hourly_data}
        
        # Generate all hours (0-23)
        time_breakdown = []
        hour_totals = {}
        total_amount = 0
        
        for hour in range(24):
            hour_data = spending_by_hour.get(hour, {
                'amount': 0,
                'transaction_count': 0
            })
            
            amount = float(hour_data['amount'] or 0)
            hour_totals[hour] = amount
            total_amount += amount
            
            time_breakdown.append({
                'hour': hour,
                'hour_label': f"{hour:02d}:00-{(hour+1)%24:02d}:00",
                'amount': amount,
                'transaction_count': hour_data['transaction_count'],
                'percentage': 0  # Will be calculated after total is known
            })
        
        # Calculate percentages
        for item in time_breakdown:
            item['percentage'] = round((item['amount'] / total_amount * 100) if total_amount > 0 else 0, 2)
        
        # Calculate summary
        if hour_totals and any(amount > 0 for amount in hour_totals.values()):
            peak_hour = max(hour_totals, key=hour_totals.get)
            quietest_hour = min((h for h, a in hour_totals.items() if a > 0), key=hour_totals.get, default=None)
        else:
            peak_hour = None
            quietest_hour = None
        
        summary = {
            'peak_hour': peak_hour,
            'quietest_hour': quietest_hour,
            'total_spending': round(total_amount, 2),
            'average_per_hour': round(total_amount / 24, 2) if total_amount > 0 else 0
        }
        
        return time_breakdown, summary


