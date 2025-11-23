from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.db.models import Sum, Q
from expenses.models import Income, Expense
from drf_spectacular.utils import extend_schema
from analytics.api.v1.base import CalendarFilterMixin, get_calendar_parameters, get_calendar_response_schema


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
            
            # Calculate aggregates
            data = self._calculate_aggregates(workspace, start_datetime, end_datetime)
            
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
                {'error': 'An unexpected error occurred.', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _calculate_aggregates(self, workspace, start_datetime, end_datetime):
        """
        Calculate monthly aggregates for income and expense.
        """
        # Filter by workspace and date range
        base_filter = Q(
            workspace=workspace,
            transacted_at__gte=start_datetime,
            transacted_at__lte=end_datetime
        )
        
        # Aggregate income
        total_income = Income.objects.filter(base_filter).aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        # Aggregate expense
        total_expense = Expense.objects.filter(base_filter).aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        # Calculate difference
        difference = total_income - total_expense
        
        return {
            'total_income': float(total_income),
            'total_expense': float(total_expense),
            'difference': float(difference),
        }

