from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.db.models import Sum, Q, Count, Avg
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from expenses.models import Income, Expense
from categories.models import Category
from drf_spectacular.utils import extend_schema, OpenApiParameter
from analytics.api.v1.base import CalendarFilterMixin, get_calendar_parameters, get_calendar_response_schema, get_all_descendants
from base.utils import get_month_range
from datetime import datetime, timedelta
from typing import Dict, Any, List
from django.db.models.functions import TruncDate
import statistics


@extend_schema(
    tags=["Quick Stats"],
    parameters=get_calendar_parameters(),
    responses={200: get_calendar_response_schema({
        'quick_stats': {
            'type': 'object',
            'properties': {
                'average_income_transaction': {
                    'type': 'number',
                    'description': 'Average size of income transactions'
                },
                'average_expense_transaction': {
                    'type': 'number',
                    'description': 'Average size of expense transactions'
                },
                'most_active_category': {
                    'type': 'object',
                    'properties': {
                        'category_id': {'type': 'integer'},
                        'category_name': {'type': 'string'},
                        'category_color': {'type': 'string'},
                        'transaction_count': {'type': 'integer'},
                        'total_amount': {'type': 'number'}
                    },
                    'description': 'Category with the most transactions'
                },
                'days_until_next_income': {
                    'type': 'integer',
                    'nullable': True,
                    'description': 'Days until next expected income (if income is regular)'
                },
                'financial_goal_progress': {
                    'type': 'object',
                    'nullable': True,
                    'properties': {
                        'goal_id': {'type': 'integer'},
                        'goal_name': {'type': 'string'},
                        'target_amount': {'type': 'number'},
                        'current_amount': {'type': 'number'},
                        'progress_percentage': {'type': 'number'},
                        'remaining_amount': {'type': 'number'}
                    },
                    'description': 'Financial goal progress (if goals are set)'
                }
            }
        },
        'summary': {
            'type': 'object',
            'properties': {
                'total_income_transactions': {'type': 'integer'},
                'total_expense_transactions': {'type': 'integer'},
                'income_regularity_detected': {'type': 'boolean'}
            }
        }
    })}
)
class QuickStatsView(APIView, CalendarFilterMixin):
    """
    Get quick stats cards for dashboard overview.
    Includes average transaction sizes, most active category, days until next income, and goal progress.
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
            
            # Calculate quick stats
            quick_stats, summary = self._calculate_quick_stats(workspace, start_datetime, end_datetime)
            
            # Build response
            response_data = {
                **month_info,
                'month_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'quick_stats': quick_stats,
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
    
    def _calculate_quick_stats(self, workspace, start_datetime, end_datetime):
        """Calculate quick stats for the period."""
        # Calculate average transaction sizes
        income_stats = Income.objects.filter(
            workspace=workspace,
            transacted_at__gte=start_datetime,
            transacted_at__lte=end_datetime,
            category__type=Category.CategoryType.INCOME
        ).aggregate(
            avg_amount=Avg('amount'),
            count=Count('id')
        )
        
        expense_stats = Expense.objects.filter(
            workspace=workspace,
            transacted_at__gte=start_datetime,
            transacted_at__lte=end_datetime,
            category__type=Category.CategoryType.EXPENSE
        ).aggregate(
            avg_amount=Avg('amount'),
            count=Count('id')
        )
        
        average_income_transaction = float(income_stats['avg_amount'] or 0)
        average_expense_transaction = float(expense_stats['avg_amount'] or 0)
        total_income_transactions = income_stats['count'] or 0
        total_expense_transactions = expense_stats['count'] or 0
        
        # Find most active category (by transaction count)
        category_counts = Expense.objects.filter(
            workspace=workspace,
            transacted_at__gte=start_datetime,
            transacted_at__lte=end_datetime,
            category__type=Category.CategoryType.EXPENSE
        ).values('category').annotate(
            transaction_count=Count('id'),
            total_amount=Sum('amount')
        ).order_by('-transaction_count')[:1]
        
        most_active_category = None
        if category_counts:
            category_data = category_counts[0]
            category = Category.objects.get(id=category_data['category'])
            most_active_category = {
                'category_id': category.id,
                'category_name': category.name,
                'category_color': category.color,
                'transaction_count': category_data['transaction_count'],
                'total_amount': round(float(category_data['total_amount'] or 0), 2)
            }
        
        # Calculate days until next income (if income is regular)
        days_until_next_income = self._calculate_days_until_next_income(workspace, start_datetime, end_datetime)
        income_regularity_detected = days_until_next_income is not None
        
        # Get financial goal progress (placeholder - needs Goal model integration)
        financial_goal_progress = self._get_financial_goal_progress(workspace, start_datetime, end_datetime)
        
        quick_stats = {
            'average_income_transaction': round(average_income_transaction, 2),
            'average_expense_transaction': round(average_expense_transaction, 2),
            'most_active_category': most_active_category,
            'days_until_next_income': days_until_next_income,
            'financial_goal_progress': financial_goal_progress
        }
        
        summary = {
            'total_income_transactions': total_income_transactions,
            'total_expense_transactions': total_expense_transactions,
            'income_regularity_detected': income_regularity_detected
        }
        
        return quick_stats, summary
    
    def _calculate_days_until_next_income(self, workspace, start_datetime, end_datetime):
        """Calculate days until next expected income if income is regular."""
        # Get income transactions from the last 6 months to detect patterns
        lookback_start = start_datetime - timedelta(days=180)  # 6 months
        
        income_transactions = Income.objects.filter(
            workspace=workspace,
            transacted_at__gte=lookback_start,
            transacted_at__lte=end_datetime,
            category__type=Category.CategoryType.INCOME
        ).order_by('transacted_at')
        
        if income_transactions.count() < 3:
            return None  # Not enough data to detect pattern
        
        # Get dates of income transactions
        income_dates = [t.transacted_at.date() for t in income_transactions]
        
        # Calculate intervals between consecutive income transactions
        intervals = []
        for i in range(1, len(income_dates)):
            interval = (income_dates[i] - income_dates[i-1]).days
            intervals.append(interval)
        
        if not intervals:
            return None
        
        # Check if intervals are regular (within 3 days variance)
        avg_interval = statistics.mean(intervals)
        if avg_interval < 1 or avg_interval > 35:
            return None  # Not monthly or too frequent
        
        # Check variance
        if len(intervals) >= 2:
            variance = statistics.stdev(intervals) if len(intervals) > 1 else 0
            if variance > 3:  # Too irregular
                return None
        
        # Get last income date
        last_income_date = income_dates[-1]
        today = end_datetime.date()
        
        # Calculate next expected income date
        days_since_last = (today - last_income_date).days
        next_expected_days = int(avg_interval) - days_since_last
        
        return max(0, next_expected_days) if next_expected_days >= 0 else None
    
    def _get_financial_goal_progress(self, workspace, start_datetime, end_datetime):
        """
        Get financial goal progress.
        TODO: Implement this method to fetch from Goal model when available.
        
        Example implementation:
            from goals.models import Goal
            goal = Goal.objects.filter(
                workspace=workspace,
                status='active'
            ).first()
            if goal:
                current_amount = # Calculate based on goal type
                return {
                    'goal_id': goal.id,
                    'goal_name': goal.name,
                    'target_amount': float(goal.target_amount),
                    'current_amount': float(current_amount),
                    'progress_percentage': (current_amount / goal.target_amount * 100),
                    'remaining_amount': float(goal.target_amount - current_amount)
                }
        """
        # Placeholder: Return None to indicate no goals set
        return None


@extend_schema(
    tags=["Quick Stats"],
    parameters=get_calendar_parameters(),
    responses={200: get_calendar_response_schema({
        'recommendations': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'priority': {'type': 'integer', 'description': 'Priority order (1-5)'},
                    'type': {
                        'type': 'string',
                        'enum': ['month_over_month', 'budget_vs_actual', 'top_expenses', 'savings_rate', 'category_trends'],
                        'description': 'Type of recommendation'
                    },
                    'title': {'type': 'string'},
                    'message': {'type': 'string', 'description': 'Human-readable recommendation message'},
                    'data': {
                        'type': 'object',
                        'description': 'Relevant data for the recommendation'
                    },
                    'action_url': {'type': 'string', 'description': 'URL to view detailed data'}
                }
            },
            'description': 'Top 5 priority recommendations'
        },
        'summary': {
            'type': 'object',
            'properties': {
                'total_recommendations': {'type': 'integer'},
                'high_priority_count': {'type': 'integer'}
            }
        }
    })}
)
class PriorityRecommendationsView(APIView, CalendarFilterMixin):
    """
    Get top 5 priority recommendations for financial insights.
    Includes month-over-month comparison, budget status, top expenses, savings rate, and category trends.
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
            
            # Calculate recommendations
            recommendations, summary = self._calculate_recommendations(
                workspace, start_datetime, end_datetime, prev_start_datetime, prev_end_datetime
            )
            
            # Build response
            response_data = {
                **month_info,
                'month_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'recommendations': recommendations,
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
    
    def _calculate_recommendations(self, workspace, start_datetime, end_datetime, prev_start_datetime, prev_end_datetime):
        """Calculate top 5 priority recommendations."""
        recommendations = []
        
        # 1. Month-over-month comparison
        mom_data = self._get_month_over_month_summary(workspace, start_datetime, end_datetime, prev_start_datetime, prev_end_datetime)
        if mom_data:
            recommendations.append({
                'priority': 1,
                'type': 'month_over_month',
                'title': _('Month-over-Month Comparison'),
                'message': mom_data['message'],
                'data': mom_data,
                'action_url': '/api/v1/analytics/trends/month-over-month/'
            })
        
        # 2. Budget vs Actual (if budgets exist)
        budget_data = self._get_budget_summary(workspace, start_datetime, end_datetime)
        if budget_data:
            recommendations.append({
                'priority': 2,
                'type': 'budget_vs_actual',
                'title': _('Budget Status'),
                'message': budget_data['message'],
                'data': budget_data,
                'action_url': '/api/v1/analytics/budget-management/budget-vs-actual/'
            })
        
        # 3. Top 5 expenses
        top_expenses_data = self._get_top_expenses(workspace, start_datetime, end_datetime)
        if top_expenses_data:
            recommendations.append({
                'priority': 3,
                'type': 'top_expenses',
                'title': _('Top Expenses'),
                'message': top_expenses_data['message'],
                'data': top_expenses_data,
                'action_url': '/api/v1/analytics/insights/spending/'
            })
        
        # 4. Savings rate
        savings_rate_data = self._get_savings_rate(workspace, start_datetime, end_datetime)
        if savings_rate_data:
            recommendations.append({
                'priority': 4,
                'type': 'savings_rate',
                'title': _('Savings Rate'),
                'message': savings_rate_data['message'],
                'data': savings_rate_data,
                'action_url': '/api/v1/dashboard/overview/'
            })
        
        # 5. Category trends
        category_trends_data = self._get_category_trends_summary(workspace, start_datetime, end_datetime, prev_start_datetime, prev_end_datetime)
        if category_trends_data:
            recommendations.append({
                'priority': 5,
                'type': 'category_trends',
                'title': _('Category Trends'),
                'message': category_trends_data['message'],
                'data': category_trends_data,
                'action_url': '/api/v1/analytics/category-analysis/trends/'
            })
        
        # Sort by priority
        recommendations.sort(key=lambda x: x['priority'])
        
        # Limit to top 5
        recommendations = recommendations[:5]
        
        summary = {
            'total_recommendations': len(recommendations),
            'high_priority_count': len([r for r in recommendations if r['priority'] <= 2])
        }
        
        return recommendations, summary
    
    def _get_month_over_month_summary(self, workspace, start_datetime, end_datetime, prev_start_datetime, prev_end_datetime):
        """Get month-over-month comparison summary."""
        # Calculate current month totals
        current_income = Income.objects.filter(
            workspace=workspace,
            transacted_at__gte=start_datetime,
            transacted_at__lte=end_datetime,
            category__type=Category.CategoryType.INCOME
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        current_expense = Expense.objects.filter(
            workspace=workspace,
            transacted_at__gte=start_datetime,
            transacted_at__lte=end_datetime,
            category__type=Category.CategoryType.EXPENSE
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Calculate previous month totals
        prev_income = Income.objects.filter(
            workspace=workspace,
            transacted_at__gte=prev_start_datetime,
            transacted_at__lte=prev_end_datetime,
            category__type=Category.CategoryType.INCOME
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        prev_expense = Expense.objects.filter(
            workspace=workspace,
            transacted_at__gte=prev_start_datetime,
            transacted_at__lte=prev_end_datetime,
            category__type=Category.CategoryType.EXPENSE
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Calculate changes
        income_change = ((current_income - prev_income) / prev_income * 100) if prev_income > 0 else 0
        expense_change = ((current_expense - prev_expense) / prev_expense * 100) if prev_expense > 0 else 0
        
        # Generate message
        if abs(income_change) >= 10 or abs(expense_change) >= 10:
            message_parts = []
            if abs(income_change) >= 10:
                direction = _("increased") if income_change > 0 else _("decreased")
                message_parts.append(_("Income {direction} by {percentage}%").format(
                    direction=direction, percentage=f"{abs(income_change):.0f}"
                ))
            if abs(expense_change) >= 10:
                direction = _("increased") if expense_change > 0 else _("decreased")
                message_parts.append(_("Expenses {direction} by {percentage}%").format(
                    direction=direction, percentage=f"{abs(expense_change):.0f}"
                ))
            
            message = _(" vs last month: {changes}").format(changes=", ".join(message_parts))
        else:
            message = _("Financial activity is stable compared to last month")
        
        return {
            'current_income': round(float(current_income), 2),
            'current_expense': round(float(current_expense), 2),
            'previous_income': round(float(prev_income), 2),
            'previous_expense': round(float(prev_expense), 2),
            'income_change_percentage': round(income_change, 2),
            'expense_change_percentage': round(expense_change, 2),
            'message': message
        }
    
    def _get_budget_summary(self, workspace, start_datetime, end_datetime):
        """Get budget vs actual summary."""
        # TODO: This should check if budgets exist
        # For now, return None if no budgets are detected
        # In a real implementation, you would check:
        # from budgets.models import Budget
        # has_budgets = Budget.objects.filter(workspace=workspace).exists()
        
        # Placeholder: Return None to indicate no budgets
        # When budgets are implemented, return summary data
        return None
    
    def _get_top_expenses(self, workspace, start_datetime, end_datetime):
        """Get top 5 expenses summary."""
        top_expenses = Expense.objects.filter(
            workspace=workspace,
            transacted_at__gte=start_datetime,
            transacted_at__lte=end_datetime,
            category__type=Category.CategoryType.EXPENSE
        ).select_related('category').order_by('-amount')[:5]
        
        if not top_expenses:
            return None
        
        expenses_list = []
        total_top_expenses = 0
        for expense in top_expenses:
            expenses_list.append({
                'id': expense.id,
                'amount': round(float(expense.amount), 2),
                'category_name': expense.category.name,
                'category_color': expense.category.color,
                'date': expense.transacted_at.date().isoformat(),
                'notes': expense.notes or ''
            })
            total_top_expenses += float(expense.amount)
        
        message = _("Top 5 expenses total {total}. Largest: {category} ({amount})").format(
            total=f"{total_top_expenses:,.2f}",
            category=expenses_list[0]['category_name'],
            amount=f"{expenses_list[0]['amount']:,.2f}"
        )
        
        return {
            'expenses': expenses_list,
            'total_amount': round(total_top_expenses, 2),
            'count': len(expenses_list),
            'message': message
        }
    
    def _get_savings_rate(self, workspace, start_datetime, end_datetime):
        """Get savings rate summary."""
        total_income = Income.objects.filter(
            workspace=workspace,
            transacted_at__gte=start_datetime,
            transacted_at__lte=end_datetime,
            category__type=Category.CategoryType.INCOME
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        total_expense = Expense.objects.filter(
            workspace=workspace,
            transacted_at__gte=start_datetime,
            transacted_at__lte=end_datetime,
            category__type=Category.CategoryType.EXPENSE
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        if total_income == 0:
            return None
        
        savings = total_income - total_expense
        savings_rate = (savings / total_income * 100) if total_income > 0 else 0
        
        # Generate message based on savings rate
        if savings_rate >= 20:
            message = _("Excellent savings rate of {rate}%! You're saving {amount} this month.").format(
                rate=f"{savings_rate:.1f}",
                amount=f"{savings:,.2f}"
            )
        elif savings_rate >= 10:
            message = _("Good savings rate of {rate}%. You're saving {amount} this month.").format(
                rate=f"{savings_rate:.1f}",
                amount=f"{savings:,.2f}"
            )
        elif savings_rate > 0:
            message = _("Savings rate of {rate}%. You're saving {amount} this month.").format(
                rate=f"{savings_rate:.1f}",
                amount=f"{savings:,.2f}"
            )
        else:
            message = _("Negative savings rate of {rate}%. Expenses exceed income by {amount}.").format(
                rate=f"{savings_rate:.1f}",
                amount=f"{abs(savings):,.2f}"
            )
        
        return {
            'savings_rate': round(savings_rate, 2),
            'total_income': round(float(total_income), 2),
            'total_expense': round(float(total_expense), 2),
            'savings_amount': round(float(savings), 2),
            'message': message
        }
    
    def _get_category_trends_summary(self, workspace, start_datetime, end_datetime, prev_start_datetime, prev_end_datetime):
        """Get category trends summary."""
        # Get all main expense categories
        main_categories = Category.objects.filter(
            parent__isnull=True,
            type=Category.CategoryType.EXPENSE
        )[:5]  # Limit to top 5 for summary
        
        growing_categories = []
        shrinking_categories = []
        
        for main_category in main_categories:
            # Get all descendants
            all_categories = get_all_descendants(main_category)
            category_ids = [cat.id for cat in all_categories]
            
            # Calculate current month spending
            current_amount = Expense.objects.filter(
                workspace=workspace,
                transacted_at__gte=start_datetime,
                transacted_at__lte=end_datetime,
                category__id__in=category_ids,
                category__type=Category.CategoryType.EXPENSE
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            # Calculate previous month spending
            previous_amount = Expense.objects.filter(
                workspace=workspace,
                transacted_at__gte=prev_start_datetime,
                transacted_at__lte=prev_end_datetime,
                category__id__in=category_ids,
                category__type=Category.CategoryType.EXPENSE
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            if previous_amount == 0:
                if current_amount > 0:
                    growing_categories.append({
                        'category_name': main_category.name,
                        'change_percentage': 100.0
                    })
                continue
            
            change_percentage = ((current_amount - previous_amount) / previous_amount * 100)
            
            if change_percentage >= 20:
                growing_categories.append({
                    'category_name': main_category.name,
                    'change_percentage': round(change_percentage, 2)
                })
            elif change_percentage <= -20:
                shrinking_categories.append({
                    'category_name': main_category.name,
                    'change_percentage': round(change_percentage, 2)
                })
        
        # Generate message
        message_parts = []
        if growing_categories:
            top_growing = max(growing_categories, key=lambda x: x['change_percentage'])
            message_parts.append(_("{category} growing by {percentage}%").format(
                category=top_growing['category_name'],
                percentage=f"{top_growing['change_percentage']:.0f}"
            ))
        if shrinking_categories:
            top_shrinking = min(shrinking_categories, key=lambda x: x['change_percentage'])
            message_parts.append(_("{category} shrinking by {percentage}%").format(
                category=top_shrinking['category_name'],
                percentage=f"{abs(top_shrinking['change_percentage']):.0f}"
            ))
        
        if not message_parts:
            message = _("Category spending is relatively stable")
        else:
            message = _("Category trends: {trends}").format(trends=", ".join(message_parts))
        
        return {
            'growing_categories': growing_categories,
            'shrinking_categories': shrinking_categories,
            'message': message
        }


