from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.db.models import Sum, Q
from expenses.models import Income, Expense
from categories.models import Category
from drf_spectacular.utils import extend_schema
from analytics.api.v1.base import CalendarFilterMixin, get_calendar_parameters, get_calendar_response_schema, get_all_descendants


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
        print(workspace)
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
        
        return {
            'total_income': float(total_income),
            'total_expense': float(total_expense),
            'difference': float(difference),
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
                {'error': 'An unexpected error occurred.', 'detail': str(e)},
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
                {'error': 'An unexpected error occurred.', 'detail': str(e)},
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

