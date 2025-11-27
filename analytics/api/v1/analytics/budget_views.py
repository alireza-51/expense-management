from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.db.models import Sum, Q, Count
from django.utils import timezone
from expenses.models import Income, Expense
from categories.models import Category
from drf_spectacular.utils import extend_schema, OpenApiParameter
from analytics.api.v1.base import CalendarFilterMixin, get_calendar_parameters, get_calendar_response_schema, get_all_descendants
from datetime import datetime, timedelta
from typing import Dict, Any

@extend_schema(
    tags=["Budget Management"],
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
                    'budget_amount': {'type': 'number'},
                    'actual_amount': {'type': 'number'},
                    'remaining': {'type': 'number'},
                    'utilization_percentage': {'type': 'number'},
                    'status': {'type': 'string', 'enum': ['under', 'warning', 'exceeded']},
                    'over_under': {'type': 'number', 'description': 'Positive if over budget, negative if under'}
                }
            }
        },
        'summary': {
            'type': 'object',
            'properties': {
                'total_budget': {'type': 'number'},
                'total_actual': {'type': 'number'},
                'total_remaining': {'type': 'number'},
                'overall_utilization': {'type': 'number'}
            }
        }
    })}
)
class BudgetVsActualView(APIView, CalendarFilterMixin):
    """
    Get budget vs actual spending for each category with progress indicators.
    Shows over/under budget status for each category.
    Supports both Jalali and Gregorian calendars.
    
    Note: This endpoint assumes budgets are stored per category. If no budgets exist,
    it will return empty data. Connect this to your Budget model when available.
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
            
            # Get budget vs actual data
            categories_data, summary = self._calculate_budget_vs_actual(
                workspace, start_datetime, end_datetime
            )
            
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
    
    def _calculate_budget_vs_actual(self, workspace, start_datetime, end_datetime):
        """
        Calculate budget vs actual for each category.
        TODO: Connect to Budget model when available.
        For now, returns structure ready for budget integration.
        """
        # Get all main expense categories
        main_categories = Category.objects.filter(
            parent__isnull=True,
            type=Category.CategoryType.EXPENSE
        )
        
        categories_data = []
        total_budget = 0
        total_actual = 0
        
        for main_category in main_categories:
            # Get all descendants including the main category itself
            all_categories = get_all_descendants(main_category)
            category_ids = [cat.id for cat in all_categories]
            
            # Calculate actual spending
            actual_amount = Expense.objects.filter(
                workspace=workspace,
                transacted_at__gte=start_datetime,
                transacted_at__lte=end_datetime,
                category__id__in=category_ids,
                category__type=Category.CategoryType.EXPENSE
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            # TODO: Get budget amount from Budget model
            # For now, return None to indicate no budget set
            budget_amount = self._get_budget_for_category(main_category, workspace, start_datetime)
            
            if budget_amount is None and actual_amount == 0:
                # Skip categories with no budget and no spending
                continue
            
            # Use 0 if no budget is set
            budget_amount = budget_amount or 0
            
            remaining = budget_amount - actual_amount
            utilization_percentage = (actual_amount / budget_amount * 100) if budget_amount > 0 else 0
            
            # Determine status
            if budget_amount == 0:
                status = 'no_budget'
            elif utilization_percentage >= 100:
                status = 'exceeded'
            elif utilization_percentage >= 80:
                status = 'warning'
            else:
                status = 'under'
            
            over_under = actual_amount - budget_amount
            
            categories_data.append({
                'category_id': main_category.id,
                'category_name': main_category.name,
                'category_color': main_category.color,
                'budget_amount': float(budget_amount),
                'actual_amount': float(actual_amount),
                'remaining': float(remaining),
                'utilization_percentage': round(utilization_percentage, 2),
                'status': status,
                'over_under': float(over_under)
            })
            
            total_budget += budget_amount
            total_actual += actual_amount
        
        # Calculate summary
        total_remaining = total_budget - total_actual
        overall_utilization = (total_actual / total_budget * 100) if total_budget > 0 else 0
        
        summary = {
            'total_budget': round(float(total_budget), 2),
            'total_actual': round(float(total_actual), 2),
            'total_remaining': round(float(total_remaining), 2),
            'overall_utilization': round(overall_utilization, 2)
        }
        
        return categories_data, summary
    
    def _get_budget_for_category(self, category, workspace, start_datetime):
        """
        Get budget amount for a category.
        TODO: Implement this method to fetch from Budget model.
        
        Example implementation:
            from budgets.models import Budget
            budget = Budget.objects.filter(
                category=category,
                workspace=workspace,
                month=start_datetime.date().replace(day=1)
            ).first()
            return float(budget.amount) if budget else None
        """
        # Placeholder: Return None to indicate no budget set
        # Replace this with actual Budget model query when available
        return None


@extend_schema(
    tags=["Budget Management"],
    parameters=get_calendar_parameters(),
    responses={200: get_calendar_response_schema({
        'overall_utilization': {
            'type': 'number',
            'description': 'Overall budget utilization percentage'
        },
        'total_budget': {'type': 'number'},
        'total_spent': {'type': 'number'},
        'total_remaining': {'type': 'number'},
        'utilization_status': {
            'type': 'string',
            'enum': ['healthy', 'warning', 'critical'],
            'description': 'Overall budget health status'
        },
        'by_category': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'category_id': {'type': 'integer'},
                    'category_name': {'type': 'string'},
                    'utilization_percentage': {'type': 'number'},
                    'status': {'type': 'string'}
                }
            }
        }
    })}
)
class BudgetUtilizationView(APIView, CalendarFilterMixin):
    """
    Get overall budget utilization percentage with visual indicators.
    Shows budget usage across all categories.
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
            
            # Calculate utilization
            utilization_data = self._calculate_utilization(workspace, start_datetime, end_datetime)
            
            # Build response
            response_data = {
                **month_info,
                'month_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                **utilization_data
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
    
    def _calculate_utilization(self, workspace, start_datetime, end_datetime):
        """Calculate budget utilization."""
        # Get all main expense categories
        main_categories = Category.objects.filter(
            parent__isnull=True,
            type=Category.CategoryType.EXPENSE
        )
        
        total_budget = 0
        total_spent = 0
        by_category = []
        
        for main_category in main_categories:
            # Get all descendants
            all_categories = get_all_descendants(main_category)
            category_ids = [cat.id for cat in all_categories]
            
            # Calculate actual spending
            actual_amount = Expense.objects.filter(
                workspace=workspace,
                transacted_at__gte=start_datetime,
                transacted_at__lte=end_datetime,
                category__id__in=category_ids,
                category__type=Category.CategoryType.EXPENSE
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            # Get budget
            budget_amount = self._get_budget_for_category(main_category, workspace, start_datetime) or 0
            
            if budget_amount > 0:
                utilization_percentage = (actual_amount / budget_amount * 100) if budget_amount > 0 else 0
                
                # Determine status
                if utilization_percentage >= 100:
                    status = 'exceeded'
                elif utilization_percentage >= 80:
                    status = 'warning'
                else:
                    status = 'healthy'
                
                by_category.append({
                    'category_id': main_category.id,
                    'category_name': main_category.name,
                    'utilization_percentage': round(utilization_percentage, 2),
                    'status': status
                })
                
                total_budget += budget_amount
                total_spent += actual_amount
        
        # Calculate overall utilization
        overall_utilization = (total_spent / total_budget * 100) if total_budget > 0 else 0
        
        # Determine overall status
        if overall_utilization >= 100:
            utilization_status = 'critical'
        elif overall_utilization >= 80:
            utilization_status = 'warning'
        else:
            utilization_status = 'healthy'
        
        return {
            'overall_utilization': round(overall_utilization, 2),
            'total_budget': round(float(total_budget), 2),
            'total_spent': round(float(total_spent), 2),
            'total_remaining': round(float(total_budget - total_spent), 2),
            'utilization_status': utilization_status,
            'by_category': by_category
        }
    
    def _get_budget_for_category(self, category, workspace, start_datetime):
        """
        Get budget amount for a category.
        TODO: Implement this method to fetch from Budget model.
        """
        return None


@extend_schema(
    tags=["Budget Management"],
    parameters=get_calendar_parameters() + [
        OpenApiParameter(
            name='warning_threshold',
            type=float,
            location=OpenApiParameter.QUERY,
            description='Percentage threshold for warning (default: 80)',
            required=False
        ),
        OpenApiParameter(
            name='critical_threshold',
            type=float,
            location=OpenApiParameter.QUERY,
            description='Percentage threshold for critical/exceeded (default: 100)',
            required=False
        )
    ],
    responses={200: get_calendar_response_schema({
        'alerts': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'category_id': {'type': 'integer'},
                    'category_name': {'type': 'string'},
                    'category_color': {'type': 'string'},
                    'alert_type': {
                        'type': 'string',
                        'enum': ['approaching', 'exceeded'],
                        'description': 'Type of alert'
                    },
                    'budget_amount': {'type': 'number'},
                    'actual_amount': {'type': 'number'},
                    'utilization_percentage': {'type': 'number'},
                    'remaining': {'type': 'number'},
                    'message': {'type': 'string'}
                }
            }
        },
        'summary': {
            'type': 'object',
            'properties': {
                'total_alerts': {'type': 'integer'},
                'exceeded_count': {'type': 'integer'},
                'approaching_count': {'type': 'integer'}
            }
        }
    })}
)
class BudgetAlertsView(APIView, CalendarFilterMixin):
    """
    Get budget alerts for categories approaching or exceeding budget limits.
    Provides warnings for categories that need attention.
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
            
            # Get thresholds
            warning_threshold = float(request.query_params.get('warning_threshold', 80))
            critical_threshold = float(request.query_params.get('critical_threshold', 100))
            
            # Get date range
            start_datetime, end_datetime = self.get_date_range(calendar_type, month_param)
            start_date = start_datetime.date()
            end_date = end_datetime.date()
            
            # Get month information
            month_info = self.get_month_info(start_date, calendar_type)
            
            # Get alerts
            alerts, summary = self._calculate_alerts(
                workspace, start_datetime, end_datetime, warning_threshold, critical_threshold
            )
            
            # Build response
            response_data = {
                **month_info,
                'month_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'alerts': alerts,
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
    
    def _calculate_alerts(
        self, workspace, start_datetime, end_datetime, warning_threshold, critical_threshold
    ):
        """Calculate budget alerts."""
        # Get all main expense categories
        main_categories = Category.objects.filter(
            parent__isnull=True,
            type=Category.CategoryType.EXPENSE
        )
        
        alerts = []
        exceeded_count = 0
        approaching_count = 0
        
        for main_category in main_categories:
            # Get all descendants
            all_categories = get_all_descendants(main_category)
            category_ids = [cat.id for cat in all_categories]
            
            # Calculate actual spending
            actual_amount = Expense.objects.filter(
                workspace=workspace,
                transacted_at__gte=start_datetime,
                transacted_at__lte=end_datetime,
                category__id__in=category_ids,
                category__type=Category.CategoryType.EXPENSE
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            # Get budget
            budget_amount = self._get_budget_for_category(main_category, workspace, start_datetime)
            
            if budget_amount is None or budget_amount == 0:
                continue
            
            utilization_percentage = (actual_amount / budget_amount * 100) if budget_amount > 0 else 0
            remaining = budget_amount - actual_amount
            
            # Check if alert is needed
            alert_type = None
            message = None
            
            if utilization_percentage >= critical_threshold:
                alert_type = 'exceeded'
                exceeded_count += 1
                over_amount = actual_amount - budget_amount
                message = f"{main_category.name} has exceeded budget by {over_amount:,.2f}"
            elif utilization_percentage >= warning_threshold:
                alert_type = 'approaching'
                approaching_count += 1
                message = f"{main_category.name} is at {utilization_percentage:.1f}% of budget. {remaining:,.2f} remaining."
            
            if alert_type:
                alerts.append({
                    'category_id': main_category.id,
                    'category_name': main_category.name,
                    'category_color': main_category.color,
                    'alert_type': alert_type,
                    'budget_amount': float(budget_amount),
                    'actual_amount': float(actual_amount),
                    'utilization_percentage': round(utilization_percentage, 2),
                    'remaining': float(remaining),
                    'message': message
                })
        
        # Sort alerts: exceeded first, then by utilization percentage
        alerts.sort(key=lambda x: (x['alert_type'] != 'exceeded', -x['utilization_percentage']))
        
        summary = {
            'total_alerts': len(alerts),
            'exceeded_count': exceeded_count,
            'approaching_count': approaching_count
        }
        
        return alerts, summary
    
    def _get_budget_for_category(self, category, workspace, start_datetime):
        """
        Get budget amount for a category.
        TODO: Implement this method to fetch from Budget model.
        """
        return None

