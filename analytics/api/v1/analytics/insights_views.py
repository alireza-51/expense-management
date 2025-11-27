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
from typing import Dict, Any, List
from django.db.models.functions import Extract, TruncDate


@extend_schema(
    tags=["Insights"],
    parameters=get_calendar_parameters(),
    responses={200: get_calendar_response_schema({
        'insights': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'category_id': {'type': 'integer'},
                    'category_name': {'type': 'string'},
                    'category_color': {'type': 'string'},
                    'insight_type': {
                        'type': 'string',
                        'enum': ['increase', 'decrease', 'new_spending', 'no_spending'],
                        'description': 'Type of insight'
                    },
                    'message': {'type': 'string', 'description': 'Human-readable insight message'},
                    'current_amount': {'type': 'number'},
                    'previous_amount': {'type': 'number'},
                    'change_percentage': {'type': 'number', 'description': 'Percentage change from previous month'},
                    'change_amount': {'type': 'number', 'description': 'Absolute change amount'}
                }
            },
            'description': 'Spending insights comparing current month with previous month'
        },
        'summary': {
            'type': 'object',
            'properties': {
                'total_insights': {'type': 'integer'},
                'significant_increases': {'type': 'integer'},
                'significant_decreases': {'type': 'integer'}
            }
        }
    })}
)
class SpendingInsightsView(APIView, CalendarFilterMixin):
    """
    Get spending insights comparing current month with previous month.
    Provides human-readable insights like "You spent 20% more on dining this month".
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
            
            # Calculate insights
            insights, summary = self._calculate_insights(
                workspace, start_datetime, end_datetime, prev_start_datetime, prev_end_datetime
            )
            
            # Build response
            response_data = {
                **month_info,
                'month_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'insights': insights,
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
    
    def _calculate_insights(self, workspace, start_datetime, end_datetime, prev_start_datetime, prev_end_datetime):
        """Calculate spending insights by comparing current and previous month."""
        # Get all main expense categories
        main_categories = Category.objects.filter(
            parent__isnull=True,
            type=Category.CategoryType.EXPENSE
        )
        
        insights = []
        significant_increases = 0
        significant_decreases = 0
        
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
            
            # Determine insight type and generate message
            insight_type = None
            message = None
            change_percentage = 0
            change_amount = current_amount - previous_amount
            
            if current_amount == 0 and previous_amount == 0:
                continue  # Skip categories with no spending in either month
            elif current_amount > 0 and previous_amount == 0:
                insight_type = 'new_spending'
                message = f"You started spending on {main_category.name} this month ({current_amount:,.2f})"
            elif current_amount == 0 and previous_amount > 0:
                insight_type = 'no_spending'
                message = f"You stopped spending on {main_category.name} this month (saved {previous_amount:,.2f})"
            elif current_amount > previous_amount:
                insight_type = 'increase'
                change_percentage = ((current_amount - previous_amount) / previous_amount * 100) if previous_amount > 0 else 100
                if change_percentage >= 20:  # Only show significant increases
                    significant_increases += 1
                    message = f"You spent {change_percentage:.0f}% more on {main_category.name} this month ({change_amount:,.2f} more)"
            elif current_amount < previous_amount:
                insight_type = 'decrease'
                change_percentage = ((current_amount - previous_amount) / previous_amount * 100) if previous_amount > 0 else 0
                if abs(change_percentage) >= 20:  # Only show significant decreases
                    significant_decreases += 1
                    message = f"You spent {abs(change_percentage):.0f}% less on {main_category.name} this month ({abs(change_amount):,.2f} less)"
            
            # Only include insights with significant changes or new/stopped spending
            if insight_type and (abs(change_percentage) >= 20 or insight_type in ['new_spending', 'no_spending']):
                insights.append({
                    'category_id': main_category.id,
                    'category_name': main_category.name,
                    'category_color': main_category.color,
                    'insight_type': insight_type,
                    'message': message,
                    'current_amount': round(float(current_amount), 2),
                    'previous_amount': round(float(previous_amount), 2),
                    'change_percentage': round(change_percentage, 2),
                    'change_amount': round(float(change_amount), 2)
                })
        
        # Sort by absolute change amount (descending)
        insights.sort(key=lambda x: abs(x['change_amount']), reverse=True)
        
        summary = {
            'total_insights': len(insights),
            'significant_increases': significant_increases,
            'significant_decreases': significant_decreases
        }
        
        return insights, summary


@extend_schema(
    tags=["Insights"],
    parameters=get_calendar_parameters() + [
        OpenApiParameter(
            name='spike_threshold',
            type=float,
            location=OpenApiParameter.QUERY,
            description='Percentage threshold to consider a spike (default: 50)',
            required=False
        ),
        OpenApiParameter(
            name='lookback_months',
            type=int,
            location=OpenApiParameter.QUERY,
            description='Number of months to look back for baseline (default: 3)',
            required=False
        )
    ],
    responses={200: get_calendar_response_schema({
        'opportunities': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'category_id': {'type': 'integer'},
                    'category_name': {'type': 'string'},
                    'category_color': {'type': 'string'},
                    'current_amount': {'type': 'number'},
                    'average_amount': {'type': 'number', 'description': 'Average spending over lookback period'},
                    'spike_percentage': {'type': 'number', 'description': 'Percentage above average'},
                    'potential_savings': {'type': 'number', 'description': 'Potential savings if spending returns to average'},
                    'message': {'type': 'string'}
                }
            },
            'description': 'Categories with unusual spending spikes'
        },
        'summary': {
            'type': 'object',
            'properties': {
                'total_opportunities': {'type': 'integer'},
                'total_potential_savings': {'type': 'number'}
            }
        }
    })}
)
class SavingsOpportunitiesView(APIView, CalendarFilterMixin):
    """
    Get savings opportunities by identifying categories with unusual spending spikes.
    Compares current month spending with historical average to find anomalies.
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
            
            # Get thresholds
            spike_threshold = float(request.query_params.get('spike_threshold', 50))
            lookback_months = int(request.query_params.get('lookback_months', 3))
            lookback_months = min(max(lookback_months, 1), 12)  # Clamp between 1 and 12
            
            # Get workspace
            workspace = self.get_workspace(request)
            
            # Get current month date range
            start_datetime, end_datetime = self.get_date_range(calendar_type, month_param)
            start_date = start_datetime.date()
            end_date = end_datetime.date()
            
            # Get month information
            month_info = self.get_month_info(start_date, calendar_type)
            
            # Calculate savings opportunities
            opportunities, summary = self._calculate_savings_opportunities(
                workspace, start_datetime, end_datetime, calendar_type, month_param, 
                spike_threshold, lookback_months
            )
            
            # Build response
            response_data = {
                **month_info,
                'month_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'opportunities': opportunities,
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
    
    def _calculate_savings_opportunities(
        self, workspace, start_datetime, end_datetime, calendar_type, month_param, 
        spike_threshold, lookback_months
    ):
        """Calculate savings opportunities by finding spending spikes."""
        # Get all main expense categories
        main_categories = Category.objects.filter(
            parent__isnull=True,
            type=Category.CategoryType.EXPENSE
        )
        
        opportunities = []
        total_potential_savings = 0
        
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
            
            if current_amount == 0:
                continue
            
            # Calculate average spending over lookback period (excluding current month)
            monthly_amounts = []
            for i in range(1, lookback_months + 1):
                month_offset = -i
                
                # Get date range for this month
                hist_start_date, hist_end_date = get_month_range(
                    calendar_type=calendar_type,
                    month_offset=month_offset,
                    specific_date=month_param
                )
                
                hist_start_datetime = timezone.make_aware(
                    datetime.combine(hist_start_date, datetime.min.time())
                )
                hist_end_datetime = timezone.make_aware(
                    datetime.combine(hist_end_date, datetime.max.time())
                )
                
                # Calculate spending for this historical month
                hist_amount = Expense.objects.filter(
                    workspace=workspace,
                    transacted_at__gte=hist_start_datetime,
                    transacted_at__lte=hist_end_datetime,
                    category__id__in=category_ids,
                    category__type=Category.CategoryType.EXPENSE
                ).aggregate(total=Sum('amount'))['total'] or 0
                
                monthly_amounts.append(float(hist_amount))
            
            # Calculate average
            if not monthly_amounts or all(amt == 0 for amt in monthly_amounts):
                continue  # No historical data
            
            average_amount = sum(monthly_amounts) / len(monthly_amounts)
            
            if average_amount == 0:
                continue  # Can't compare if no historical average
            
            # Check if current spending is a spike
            spike_percentage = ((current_amount - average_amount) / average_amount * 100) if average_amount > 0 else 0
            
            if spike_percentage >= spike_threshold:
                potential_savings = current_amount - average_amount
                total_potential_savings += potential_savings
                
                opportunities.append({
                    'category_id': main_category.id,
                    'category_name': main_category.name,
                    'category_color': main_category.color,
                    'current_amount': round(float(current_amount), 2),
                    'average_amount': round(average_amount, 2),
                    'spike_percentage': round(spike_percentage, 2),
                    'potential_savings': round(float(potential_savings), 2),
                    'message': f"{main_category.name} spending is {spike_percentage:.0f}% above average. Potential savings: {potential_savings:,.2f}"
                })
        
        # Sort by potential savings (descending)
        opportunities.sort(key=lambda x: x['potential_savings'], reverse=True)
        
        summary = {
            'total_opportunities': len(opportunities),
            'total_potential_savings': round(total_potential_savings, 2)
        }
        
        return opportunities, summary


@extend_schema(
    tags=["Insights"],
    parameters=get_calendar_parameters() + [
        OpenApiParameter(
            name='min_occurrences',
            type=int,
            location=OpenApiParameter.QUERY,
            description='Minimum number of occurrences to consider recurring (default: 3)',
            required=False
        ),
        OpenApiParameter(
            name='lookback_months',
            type=int,
            location=OpenApiParameter.QUERY,
            description='Number of months to look back for pattern detection (default: 6)',
            required=False
        )
    ],
    responses={200: get_calendar_response_schema({
        'recurring_expenses': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'category_id': {'type': 'integer'},
                    'category_name': {'type': 'string'},
                    'category_color': {'type': 'string'},
                    'average_amount': {'type': 'number', 'description': 'Average amount per occurrence'},
                    'frequency': {'type': 'string', 'description': 'Frequency pattern (monthly, bi-weekly, etc.)'},
                    'occurrences': {'type': 'integer', 'description': 'Number of occurrences in lookback period'},
                    'total_amount': {'type': 'number', 'description': 'Total amount over lookback period'},
                    'next_expected_date': {'type': 'string', 'format': 'date', 'description': 'Expected next occurrence date'},
                    'is_subscription': {'type': 'boolean', 'description': 'Likely a subscription based on pattern'}
                }
            },
            'description': 'List of recurring expenses identified'
        },
        'summary': {
            'type': 'object',
            'properties': {
                'total_recurring': {'type': 'integer'},
                'total_monthly_cost': {'type': 'number', 'description': 'Estimated monthly cost of all recurring expenses'},
                'subscriptions_count': {'type': 'integer'}
            }
        }
    })}
)
class RecurringExpensesView(APIView, CalendarFilterMixin):
    """
    Get recurring expenses summary by identifying patterns in spending.
    Detects subscriptions, bills, and other recurring expenses based on transaction patterns.
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
            
            # Get parameters
            min_occurrences = int(request.query_params.get('min_occurrences', 3))
            lookback_months = int(request.query_params.get('lookback_months', 6))
            lookback_months = min(max(lookback_months, 1), 12)  # Clamp between 1 and 12
            
            # Get workspace
            workspace = self.get_workspace(request)
            
            # Get current month date range (for reference)
            start_datetime, end_datetime = self.get_date_range(calendar_type, month_param)
            start_date = start_datetime.date()
            end_date = end_datetime.date()
            
            # Get month information
            month_info = self.get_month_info(start_date, calendar_type)
            
            # Calculate recurring expenses
            recurring_expenses, summary = self._calculate_recurring_expenses(
                workspace, calendar_type, month_param, lookback_months, min_occurrences
            )
            
            # Build response
            response_data = {
                **month_info,
                'month_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'recurring_expenses': recurring_expenses,
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
    
    def _calculate_recurring_expenses(
        self, workspace, calendar_type, month_param, lookback_months, min_occurrences
    ):
        """Calculate recurring expenses by analyzing patterns."""
        # Get all expense categories
        categories = Category.objects.filter(
            type=Category.CategoryType.EXPENSE
        )
        
        recurring_expenses = []
        total_monthly_cost = 0
        subscriptions_count = 0
        
        # Calculate lookback period end date (current month)
        current_start_date, current_end_date = get_month_range(
            calendar_type=calendar_type,
            month_offset=0,
            specific_date=month_param
        )
        
        # Calculate lookback period start date
        lookback_start_date, _ = get_month_range(
            calendar_type=calendar_type,
            month_offset=-(lookback_months - 1),
            specific_date=month_param
        )
        
        lookback_start_datetime = timezone.make_aware(
            datetime.combine(lookback_start_date, datetime.min.time())
        )
        lookback_end_datetime = timezone.make_aware(
            datetime.combine(current_end_date, datetime.max.time())
        )
        
        for category in categories:
            # Get all transactions for this category in lookback period
            transactions = Expense.objects.filter(
                workspace=workspace,
                transacted_at__gte=lookback_start_datetime,
                transacted_at__lte=lookback_end_datetime,
                category=category,
                category__type=Category.CategoryType.EXPENSE
            ).order_by('transacted_at')
            
            if transactions.count() < min_occurrences:
                continue
            
            # Group transactions by similar amount (within 10% variance)
            amount_groups = []
            for transaction in transactions:
                amount = float(transaction.amount)
                # Find matching group
                matched = False
                for group in amount_groups:
                    group_amount = float(group[0].amount)
                    if abs(amount - group_amount) / group_amount <= 0.1:  # Within 10%
                        group.append(transaction)
                        matched = True
                        break
                if not matched:
                    amount_groups.append([transaction])
            
            # Find the largest group (most recurring pattern)
            if not amount_groups:
                continue
            
            largest_group = max(amount_groups, key=len)
            
            if len(largest_group) < min_occurrences:
                continue
            
            # Calculate statistics
            amounts = [float(t.amount) for t in largest_group]
            average_amount = sum(amounts) / len(amounts)
            total_amount = sum(amounts)
            
            # Determine frequency pattern
            dates = [t.transacted_at.date() for t in largest_group]
            dates.sort()
            
            # Calculate average days between transactions
            if len(dates) >= 2:
                days_between = []
                for i in range(1, len(dates)):
                    days_between.append((dates[i] - dates[i-1]).days)
                avg_days = sum(days_between) / len(days_between) if days_between else 0
                
                # Determine frequency
                if 25 <= avg_days <= 35:
                    frequency = 'monthly'
                    is_subscription = True
                elif 12 <= avg_days <= 16:
                    frequency = 'bi-weekly'
                    is_subscription = True
                elif 6 <= avg_days <= 8:
                    frequency = 'weekly'
                    is_subscription = False
                elif 85 <= avg_days <= 95:
                    frequency = 'quarterly'
                    is_subscription = True
                else:
                    frequency = 'irregular'
                    is_subscription = False
            else:
                frequency = 'unknown'
                is_subscription = False
                avg_days = 0
            
            # Calculate next expected date
            if dates and avg_days > 0:
                last_date = dates[-1]
                next_expected_date = last_date + timedelta(days=int(avg_days))
            else:
                next_expected_date = None
            
            # Estimate monthly cost
            if frequency == 'monthly':
                monthly_cost = average_amount
            elif frequency == 'bi-weekly':
                monthly_cost = average_amount * 2.17  # Approx 2.17 bi-weekly periods per month
            elif frequency == 'weekly':
                monthly_cost = average_amount * 4.33  # Approx 4.33 weeks per month
            elif frequency == 'quarterly':
                monthly_cost = average_amount / 3
            else:
                monthly_cost = average_amount  # Default to amount itself
            
            total_monthly_cost += monthly_cost
            
            if is_subscription:
                subscriptions_count += 1
            
            recurring_expenses.append({
                'category_id': category.id,
                'category_name': category.name,
                'category_color': category.color,
                'average_amount': round(average_amount, 2),
                'frequency': frequency,
                'occurrences': len(largest_group),
                'total_amount': round(total_amount, 2),
                'next_expected_date': next_expected_date.isoformat() if next_expected_date else None,
                'is_subscription': is_subscription
            })
        
        # Sort by monthly cost (descending)
        recurring_expenses.sort(key=lambda x: x['average_amount'] * (2.17 if x['frequency'] == 'bi-weekly' else (4.33 if x['frequency'] == 'weekly' else (1/3 if x['frequency'] == 'quarterly' else 1))), reverse=True)
        
        summary = {
            'total_recurring': len(recurring_expenses),
            'total_monthly_cost': round(total_monthly_cost, 2),
            'subscriptions_count': subscriptions_count
        }
        
        return recurring_expenses, summary

