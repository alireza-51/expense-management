from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.db.models import Sum, Q, Count
from django.db import models
from django.utils import timezone
from expenses.models import Income, Expense
from categories.models import Category
from drf_spectacular.utils import extend_schema, OpenApiParameter
from analytics.api.v1.base import CalendarFilterMixin, get_calendar_parameters, get_calendar_response_schema, get_all_descendants
from base.utils import get_month_range
from datetime import datetime, timedelta
import jdatetime
from typing import Dict, Any, List
from django.db.models.functions import Extract, TruncDate, TruncHour, TruncDay


@extend_schema(
    tags=["Trends"],
    parameters=get_calendar_parameters(),
    responses={200: {
        'type': 'object',
        'properties': {
            'current_month': {
                'type': 'object',
                'properties': {
                    'month': {'type': 'string'},
                    'total_income': {'type': 'number'},
                    'total_expense': {'type': 'number'},
                    'difference': {'type': 'number'},
                }
            },
            'previous_month': {
                'type': 'object',
                'properties': {
                    'month': {'type': 'string'},
                    'total_income': {'type': 'number'},
                    'total_expense': {'type': 'number'},
                    'difference': {'type': 'number'},
                }
            },
            'comparison': {
                'type': 'object',
                'properties': {
                    'income_change': {'type': 'number', 'description': 'Percentage change in income'},
                    'expense_change': {'type': 'number', 'description': 'Percentage change in expense'},
                    'difference_change': {'type': 'number', 'description': 'Absolute change in difference'},
                }
            }
        }
    }}
)
class MonthOverMonthComparisonView(APIView, CalendarFilterMixin):
    """
    Compare current month with previous month (income, expenses, balance) with percentage changes.
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
            
            # Get current month date range
            start_datetime, end_datetime = self.get_date_range(calendar_type, month_param)
            start_date = start_datetime.date()
            end_date = end_datetime.date()
            
            # Get previous month date range
            prev_start_date, prev_end_date = get_month_range(
                calendar_type=calendar_type,
                month_offset=-1,
                specific_date=month_param
            )
            prev_start_datetime = timezone.make_aware(
                datetime.combine(prev_start_date, datetime.min.time())
            )
            prev_end_datetime = timezone.make_aware(
                datetime.combine(prev_end_date, datetime.max.time())
            )
            
            # Get month information
            month_info = self.get_month_info(start_date, calendar_type)
            prev_month_info = self.get_month_info(prev_start_date, calendar_type)
            
            # Calculate aggregates for both months
            current_data = self._calculate_month_aggregates(workspace, start_datetime, end_datetime)
            previous_data = self._calculate_month_aggregates(workspace, prev_start_datetime, prev_end_datetime)
            
            # Calculate percentage changes
            comparison = self._calculate_comparison(current_data, previous_data)
            
            # Build response
            response_data = {
                'current_month': {
                    **month_info,
                    **current_data
                },
                'previous_month': {
                    **prev_month_info,
                    **previous_data
                },
                'comparison': comparison
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
    
    def _calculate_month_aggregates(self, workspace, start_datetime, end_datetime):
        """Calculate aggregates for a given month."""
        base_filter = Q(
            workspace=workspace,
            transacted_at__gte=start_datetime,
            transacted_at__lte=end_datetime
        )
        
        total_income = Income.objects.filter(
            base_filter, 
            category__type=Category.CategoryType.INCOME
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        total_expense = Expense.objects.filter(
            base_filter, 
            category__type=Category.CategoryType.EXPENSE
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        difference = total_income - total_expense
        
        return {
            'total_income': float(total_income),
            'total_expense': float(total_expense),
            'difference': float(difference),
        }
    
    def _calculate_comparison(self, current: Dict[str, float], previous: Dict[str, float]) -> Dict[str, Any]:
        """Calculate percentage changes between current and previous month."""
        # Income change
        if previous['total_income'] > 0:
            income_change = ((current['total_income'] - previous['total_income']) / previous['total_income']) * 100
        else:
            income_change = 100.0 if current['total_income'] > 0 else 0.0
        
        # Expense change
        if previous['total_expense'] > 0:
            expense_change = ((current['total_expense'] - previous['total_expense']) / previous['total_expense']) * 100
        else:
            expense_change = 100.0 if current['total_expense'] > 0 else 0.0
        
        # Difference change (absolute)
        difference_change = current['difference'] - previous['difference']
        
        return {
            'income_change': round(income_change, 2),
            'expense_change': round(expense_change, 2),
            'difference_change': round(difference_change, 2),
        }


@extend_schema(
    tags=["Trends"],
    parameters=get_calendar_parameters(),
    responses={200: {
        'type': 'object',
        'properties': {
            'current_month': {
                'type': 'object',
                'properties': {
                    'month': {'type': 'string'},
                    'year': {'type': 'integer'},
                    'total_income': {'type': 'number'},
                    'total_expense': {'type': 'number'},
                    'difference': {'type': 'number'},
                }
            },
            'previous_year_month': {
                'type': 'object',
                'properties': {
                    'month': {'type': 'string'},
                    'year': {'type': 'integer'},
                    'total_income': {'type': 'number'},
                    'total_expense': {'type': 'number'},
                    'difference': {'type': 'number'},
                }
            },
            'comparison': {
                'type': 'object',
                'properties': {
                    'income_change': {'type': 'number', 'description': 'Percentage change in income'},
                    'expense_change': {'type': 'number', 'description': 'Percentage change in expense'},
                    'difference_change': {'type': 'number', 'description': 'Absolute change in difference'},
                }
            }
        }
    }}
)
class YearOverYearComparisonView(APIView, CalendarFilterMixin):
    """
    Compare current month with the same month last year (income, expenses, balance) with percentage changes.
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
            
            # Get current month date range
            start_datetime, end_datetime = self.get_date_range(calendar_type, month_param)
            start_date = start_datetime.date()
            end_date = end_datetime.date()
            
            # Get same month last year date range
            if calendar_type == 'jalali':
                if month_param:
                    year, month = map(int, month_param.split('-'))
                    prev_year_date = jdatetime.date(year - 1, month, 1)
                else:
                    today = jdatetime.date.today()
                    prev_year_date = jdatetime.date(today.year - 1, today.month, 1)
                
                # Get last day of month
                if prev_year_date.month == 12:
                    prev_end_date = jdatetime.date(prev_year_date.year + 1, 1, 1) - jdatetime.timedelta(days=1)
                else:
                    prev_end_date = jdatetime.date(prev_year_date.year, prev_year_date.month + 1, 1) - jdatetime.timedelta(days=1)
                
                prev_start_date = prev_year_date.togregorian()
                prev_end_date_greg = prev_end_date.togregorian()
            else:
                if month_param:
                    year, month = map(int, month_param.split('-'))
                    prev_year_date = datetime(year - 1, month, 1).date()
                else:
                    today = datetime.now().date()
                    prev_year_date = datetime(today.year - 1, today.month, 1).date()
                
                # Get last day of month
                if prev_year_date.month == 12:
                    prev_end_date_greg = datetime(prev_year_date.year + 1, 1, 1).date() - timedelta(days=1)
                else:
                    prev_end_date_greg = datetime(prev_year_date.year, prev_year_date.month + 1, 1).date() - timedelta(days=1)
                
                prev_start_date = prev_year_date
            
            prev_start_datetime = timezone.make_aware(
                datetime.combine(prev_start_date, datetime.min.time())
            )
            prev_end_datetime = timezone.make_aware(
                datetime.combine(prev_end_date_greg, datetime.max.time())
            )
            
            # Get month information
            month_info = self.get_month_info(start_date, calendar_type)
            prev_month_info = self.get_month_info(prev_start_date, calendar_type)
            
            # Calculate aggregates for both months
            current_data = self._calculate_month_aggregates(workspace, start_datetime, end_datetime)
            previous_data = self._calculate_month_aggregates(workspace, prev_start_datetime, prev_end_datetime)
            
            # Calculate percentage changes
            comparison = self._calculate_comparison(current_data, previous_data)
            
            # Extract year from month info
            current_year = int(month_info['month'].split('-')[0])
            prev_year = int(prev_month_info['month'].split('-')[0])
            
            # Build response
            response_data = {
                'current_month': {
                    **month_info,
                    'year': current_year,
                    **current_data
                },
                'previous_year_month': {
                    **prev_month_info,
                    'year': prev_year,
                    **previous_data
                },
                'comparison': comparison
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
    
    def _calculate_month_aggregates(self, workspace, start_datetime, end_datetime):
        """Calculate aggregates for a given month."""
        base_filter = Q(
            workspace=workspace,
            transacted_at__gte=start_datetime,
            transacted_at__lte=end_datetime
        )
        
        total_income = Income.objects.filter(
            base_filter, 
            category__type=Category.CategoryType.INCOME
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        total_expense = Expense.objects.filter(
            base_filter, 
            category__type=Category.CategoryType.EXPENSE
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        difference = total_income - total_expense
        
        return {
            'total_income': float(total_income),
            'total_expense': float(total_expense),
            'difference': float(difference),
        }
    
    def _calculate_comparison(self, current: Dict[str, float], previous: Dict[str, float]) -> Dict[str, Any]:
        """Calculate percentage changes between current and previous year month."""
        # Income change
        if previous['total_income'] > 0:
            income_change = ((current['total_income'] - previous['total_income']) / previous['total_income']) * 100
        else:
            income_change = 100.0 if current['total_income'] > 0 else 0.0
        
        # Expense change
        if previous['total_expense'] > 0:
            expense_change = ((current['total_expense'] - previous['total_expense']) / previous['total_expense']) * 100
        else:
            expense_change = 100.0 if current['total_expense'] > 0 else 0.0
        
        # Difference change (absolute)
        difference_change = current['difference'] - previous['difference']
        
        return {
            'income_change': round(income_change, 2),
            'expense_change': round(expense_change, 2),
            'difference_change': round(difference_change, 2),
        }


@extend_schema(
    tags=["Trends"],
    parameters=get_calendar_parameters() + [
        OpenApiParameter(
            name='months',
            type=int,
            location=OpenApiParameter.QUERY,
            description='Number of months to include in trend (default: 6, max: 12)',
            required=False
        )
    ],
    responses={200: {
        'type': 'object',
        'properties': {
            'trends': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'properties': {
                        'month': {'type': 'string'},
                        'month_name': {'type': 'string'},
                        'total_income': {'type': 'number'},
                        'total_expense': {'type': 'number'},
                        'difference': {'type': 'number'},
                    }
                }
            },
            'summary': {
                'type': 'object',
                'properties': {
                    'average_income': {'type': 'number'},
                    'average_expense': {'type': 'number'},
                    'average_difference': {'type': 'number'},
                    'total_months': {'type': 'integer'},
                }
            }
        }
    }}
)
class MultiMonthTrendView(APIView, CalendarFilterMixin):
    """
    Show income/expense trends over the last N months (default 6, max 12).
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
            
            # Get month parameter (end month, defaults to current)
            month_param = self.get_month_param(request)
            
            # Get number of months to include
            months_count = int(request.query_params.get('months', 6))
            months_count = min(max(months_count, 1), 12)  # Clamp between 1 and 12
            
            # Get workspace
            workspace = self.get_workspace(request)
            
            # Calculate trends for the last N months
            # If month_param is provided, it's the end month; otherwise use current month
            trends = []
            for i in range(months_count):
                # Calculate month offset (0 = current/end month, negative for previous months)
                month_offset = -(months_count - 1 - i)
                
                # Get date range for this month
                start_date, end_date = get_month_range(
                    calendar_type=calendar_type,
                    month_offset=month_offset,
                    specific_date=month_param
                )
                
                start_datetime = timezone.make_aware(
                    datetime.combine(start_date, datetime.min.time())
                )
                end_datetime = timezone.make_aware(
                    datetime.combine(end_date, datetime.max.time())
                )
                
                # Get month information
                month_info = self.get_month_info(start_date, calendar_type)
                
                # Calculate aggregates
                data = self._calculate_month_aggregates(workspace, start_datetime, end_datetime)
                
                trends.append({
                    **month_info,
                    **data
                })
            
            # Calculate summary statistics
            summary = self._calculate_summary(trends)
            
            # Build response
            response_data = {
                'trends': trends,
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
    
    def _calculate_month_aggregates(self, workspace, start_datetime, end_datetime):
        """Calculate aggregates for a given month."""
        base_filter = Q(
            workspace=workspace,
            transacted_at__gte=start_datetime,
            transacted_at__lte=end_datetime
        )
        
        total_income = Income.objects.filter(
            base_filter, 
            category__type=Category.CategoryType.INCOME
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        total_expense = Expense.objects.filter(
            base_filter, 
            category__type=Category.CategoryType.EXPENSE
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        difference = total_income - total_expense
        
        return {
            'total_income': float(total_income),
            'total_expense': float(total_expense),
            'difference': float(difference),
        }
    
    def _calculate_summary(self, trends: list) -> Dict[str, Any]:
        """Calculate summary statistics from trends."""
        if not trends:
            return {
                'average_income': 0.0,
                'average_expense': 0.0,
                'average_difference': 0.0,
                'total_months': 0,
            }
        
        total_income = sum(t['total_income'] for t in trends)
        total_expense = sum(t['total_expense'] for t in trends)
        total_difference = sum(t['difference'] for t in trends)
        count = len(trends)
        
        return {
            'average_income': round(total_income / count, 2),
            'average_expense': round(total_expense / count, 2),
            'average_difference': round(total_difference / count, 2),
            'total_months': count,
        }

