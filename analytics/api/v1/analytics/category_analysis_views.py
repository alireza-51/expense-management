from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.db.models import Sum, Q, Count
from django.utils import timezone
from expenses.models import Income, Expense
from categories.models import Category
from drf_spectacular.utils import extend_schema, OpenApiParameter
from analytics.api.v1.base import CalendarFilterMixin, get_calendar_parameters, get_calendar_response_schema, get_all_descendants
from base.utils import get_month_range
from datetime import datetime, timedelta
from typing import Dict, Any

@extend_schema(
    tags=["Category Analysis"],
    parameters=get_calendar_parameters(),
    responses={200: get_calendar_response_schema({
        'categories': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'category_id': {'type': 'integer'},
                    'category_name': {'type': 'string'},
                    'category_color': {'type': 'string'},
                    'amount': {'type': 'number', 'description': 'Total spending for this category'},
                    'transaction_count': {'type': 'integer'},
                    'percentage': {'type': 'number', 'description': 'Percentage of total expenses'}
                }
            },
            'description': 'Category comparison data for bar chart'
        },
        'summary': {
            'type': 'object',
            'properties': {
                'total_expenses': {'type': 'number'},
                'total_categories': {'type': 'integer'},
                'top_category': {'type': 'string'}
            }
        }
    })}
)
class CategoryComparisonView(APIView, CalendarFilterMixin):
    """
    Get category comparison data for side-by-side bar chart visualization.
    Shows spending amounts for each expense category.
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
            
            # Calculate category comparison
            categories_data, summary = self._calculate_category_comparison(workspace, start_datetime, end_datetime)
            
            # Build response
            response_data = {
                **month_info,
                'month_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'categories': categories_data,
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
    
    def _calculate_category_comparison(self, workspace, start_datetime, end_datetime):
        """Calculate category comparison data."""
        # Get all main expense categories
        main_categories = Category.objects.filter(
            parent__isnull=True,
            type=Category.CategoryType.EXPENSE
        )
        
        categories_data = []
        total_expenses = 0
        
        for main_category in main_categories:
            # Get all descendants including the main category itself
            all_categories = get_all_descendants(main_category)
            category_ids = [cat.id for cat in all_categories]
            
            # Calculate spending for this category and all its descendants
            amount = Expense.objects.filter(
                workspace=workspace,
                transacted_at__gte=start_datetime,
                transacted_at__lte=end_datetime,
                category__id__in=category_ids,
                category__type=Category.CategoryType.EXPENSE
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            transaction_count = Expense.objects.filter(
                workspace=workspace,
                transacted_at__gte=start_datetime,
                transacted_at__lte=end_datetime,
                category__id__in=category_ids,
                category__type=Category.CategoryType.EXPENSE
            ).count()
            
            if amount > 0:
                categories_data.append({
                    'category_id': main_category.id,
                    'category_name': main_category.name,
                    'category_color': main_category.color,
                    'amount': float(amount),
                    'transaction_count': transaction_count,
                    'percentage': 0  # Will be calculated below
                })
                total_expenses += amount
        
        # Calculate percentages
        for item in categories_data:
            item['percentage'] = round((item['amount'] / total_expenses * 100) if total_expenses > 0 else 0, 2)
        
        # Sort by amount descending
        categories_data.sort(key=lambda x: x['amount'], reverse=True)
        
        # Calculate summary
        top_category = categories_data[0]['category_name'] if categories_data else None
        
        summary = {
            'total_expenses': round(float(total_expenses), 2),
            'total_categories': len(categories_data),
            'top_category': top_category
        }
        
        return categories_data, summary


@extend_schema(
    tags=["Category Analysis"],
    parameters=get_calendar_parameters() + [
        OpenApiParameter(
            name='months',
            type=int,
            location=OpenApiParameter.QUERY,
            description='Number of months to include in trend (default: 6, max: 12)',
            required=False
        )
    ],
    responses={200: get_calendar_response_schema({
        'category_trends': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'category_id': {'type': 'integer'},
                    'category_name': {'type': 'string'},
                    'category_color': {'type': 'string'},
                    'trends': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'month': {'type': 'string'},
                                'amount': {'type': 'number'},
                                'transaction_count': {'type': 'integer'}
                            }
                        }
                    },
                    'change_percentage': {'type': 'number', 'description': 'Percentage change from first to last month'}
                }
            },
            'description': 'Category trends over multiple months'
        },
        'summary': {
            'type': 'object',
            'properties': {
                'total_months': {'type': 'integer'},
                'categories_tracked': {'type': 'integer'}
            }
        }
    })}
)
class CategoryTrendsView(APIView, CalendarFilterMixin):
    """
    Get category trends showing how each category changes month-over-month.
    Returns line chart data for category spending trends.
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
            
            # Get number of months to include
            months_count = int(request.query_params.get('months', 6))
            months_count = min(max(months_count, 1), 12)  # Clamp between 1 and 12
            
            # Get workspace
            workspace = self.get_workspace(request)
            
            # Get date range for the end month
            start_datetime, end_datetime = self.get_date_range(calendar_type, month_param)
            start_date = start_datetime.date()
            end_date = end_datetime.date()
            
            # Get month information
            month_info = self.get_month_info(start_date, calendar_type)
            
            # Calculate category trends
            category_trends, summary = self._calculate_category_trends(
                workspace, calendar_type, month_param, months_count
            )
            
            # Build response
            response_data = {
                **month_info,
                'month_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'category_trends': category_trends,
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
    
    def _calculate_category_trends(self, workspace, calendar_type, month_param, months_count):
        """Calculate category trends over multiple months."""
        # Get all main expense categories
        main_categories = Category.objects.filter(
            parent__isnull=True,
            type=Category.CategoryType.EXPENSE
        )
        
        category_trends = []
        
        for main_category in main_categories:
            # Get all descendants
            all_categories = get_all_descendants(main_category)
            category_ids = [cat.id for cat in all_categories]
            
            # Get trends for each month
            trends = []
            for i in range(months_count):
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
                
                # Get month info for display
                month_info = self.get_month_info(start_date, calendar_type)
                
                # Calculate spending for this month
                amount = Expense.objects.filter(
                    workspace=workspace,
                    transacted_at__gte=start_datetime,
                    transacted_at__lte=end_datetime,
                    category__id__in=category_ids,
                    category__type=Category.CategoryType.EXPENSE
                ).aggregate(total=Sum('amount'))['total'] or 0
                
                transaction_count = Expense.objects.filter(
                    workspace=workspace,
                    transacted_at__gte=start_datetime,
                    transacted_at__lte=end_datetime,
                    category__id__in=category_ids,
                    category__type=Category.CategoryType.EXPENSE
                ).count()
                
                trends.append({
                    'month': month_info['month'],
                    'amount': float(amount),
                    'transaction_count': transaction_count
                })
            
            # Calculate change percentage (first to last month)
            if len(trends) >= 2:
                first_amount = trends[0]['amount']
                last_amount = trends[-1]['amount']
                if first_amount > 0:
                    change_percentage = ((last_amount - first_amount) / first_amount) * 100
                else:
                    change_percentage = 100.0 if last_amount > 0 else 0.0
            else:
                change_percentage = 0.0
            
            # Only include categories that have spending in at least one month
            if any(trend['amount'] > 0 for trend in trends):
                category_trends.append({
                    'category_id': main_category.id,
                    'category_name': main_category.name,
                    'category_color': main_category.color,
                    'trends': trends,
                    'change_percentage': round(change_percentage, 2)
                })
        
        # Sort by total spending (sum of all months) descending
        category_trends.sort(
            key=lambda x: sum(t['amount'] for t in x['trends']),
            reverse=True
        )
        
        summary = {
            'total_months': months_count,
            'categories_tracked': len(category_trends)
        }
        
        return category_trends, summary


@extend_schema(
    tags=["Category Analysis"],
    parameters=get_calendar_parameters(),
    responses={200: get_calendar_response_schema({
        'categories': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'category_id': {'type': 'integer'},
                    'category_name': {'type': 'string'},
                    'category_color': {'type': 'string'},
                    'expense_amount': {'type': 'number'},
                    'income_amount': {'type': 'number'},
                    'efficiency_ratio': {
                        'type': 'number',
                        'description': 'Expense amount / Income amount (lower is better)'
                    },
                    'percentage_of_income': {
                        'type': 'number',
                        'description': 'What percentage of income is spent on this category'
                    }
                }
            },
            'description': 'Category efficiency data'
        },
        'summary': {
            'type': 'object',
            'properties': {
                'total_income': {'type': 'number'},
                'total_expenses': {'type': 'number'},
                'overall_efficiency': {'type': 'number', 'description': 'Total expenses / Total income'}
            }
        }
    })}
)
class CategoryEfficiencyView(APIView, CalendarFilterMixin):
    """
    Get category efficiency: spending per category relative to income.
    Shows how much of income is spent on each category.
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
            
            # Calculate category efficiency
            categories_data, summary = self._calculate_category_efficiency(workspace, start_datetime, end_datetime)
            
            # Build response
            response_data = {
                **month_info,
                'month_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'categories': categories_data,
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
    
    def _calculate_category_efficiency(self, workspace, start_datetime, end_datetime):
        """Calculate category efficiency relative to income."""
        # Get total income for the period
        total_income = Income.objects.filter(
            workspace=workspace,
            transacted_at__gte=start_datetime,
            transacted_at__lte=end_datetime,
            category__type=Category.CategoryType.INCOME
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Get all main expense categories
        main_categories = Category.objects.filter(
            parent__isnull=True,
            type=Category.CategoryType.EXPENSE
        )
        
        categories_data = []
        total_expenses = 0
        
        for main_category in main_categories:
            # Get all descendants
            all_categories = get_all_descendants(main_category)
            category_ids = [cat.id for cat in all_categories]
            
            # Calculate spending for this category
            expense_amount = Expense.objects.filter(
                workspace=workspace,
                transacted_at__gte=start_datetime,
                transacted_at__lte=end_datetime,
                category__id__in=category_ids,
                category__type=Category.CategoryType.EXPENSE
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            if expense_amount > 0:
                # Calculate efficiency metrics
                efficiency_ratio = (expense_amount / total_income) if total_income > 0 else 0
                percentage_of_income = (expense_amount / total_income * 100) if total_income > 0 else 0
                
                categories_data.append({
                    'category_id': main_category.id,
                    'category_name': main_category.name,
                    'category_color': main_category.color,
                    'expense_amount': float(expense_amount),
                    'income_amount': float(total_income),
                    'efficiency_ratio': round(efficiency_ratio, 4),
                    'percentage_of_income': round(percentage_of_income, 2)
                })
                
                total_expenses += expense_amount
        
        # Sort by percentage of income descending
        categories_data.sort(key=lambda x: x['percentage_of_income'], reverse=True)
        
        # Calculate summary
        overall_efficiency = (total_expenses / total_income) if total_income > 0 else 0
        
        summary = {
            'total_income': round(float(total_income), 2),
            'total_expenses': round(float(total_expenses), 2),
            'overall_efficiency': round(overall_efficiency, 4)
        }
        
        return categories_data, summary

