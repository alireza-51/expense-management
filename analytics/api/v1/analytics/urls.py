from django.urls import path
from .trends_views import (
    MonthOverMonthComparisonView,
    YearOverYearComparisonView,
    MultiMonthTrendView,
)
from .budget_views import (
    BudgetVsActualView,
    BudgetUtilizationView,
    BudgetAlertsView,
)
from .spending_patterns_views import (
    DailySpendingHeatmapView,
    WeeklyBreakdownView,
    TimeBasedAnalysisView,
)
from .category_analysis_views import (
    CategoryComparisonView,
    CategoryTrendsView,
    CategoryEfficiencyView,
)
from .cash_flow_views import (
    CashFlowTimelineView,
    IncomeVsExpenseTimelineView,
    BalanceTrendView,
)
from .insights_views import (
    SpendingInsightsView,
    SavingsOpportunitiesView,
    RecurringExpensesView,
)
from .quick_stats_views import (
    QuickStatsView,
    PriorityRecommendationsView,
)

urlpatterns = [
    path('trends/', MultiMonthTrendView.as_view(), name='multi-month-trends'),
    path('trends/month-over-month/', MonthOverMonthComparisonView.as_view(), name='month-over-month'),
    path('trends/year-over-year/', YearOverYearComparisonView.as_view(), name='year-over-year'),
    path('budget-management/budget-vs-actual/', BudgetVsActualView.as_view(), name='budget-vs-actual'),
    path('budget-management/utilization/', BudgetUtilizationView.as_view(), name='budget-utilization'),
    path('budget-management/alerts/', BudgetAlertsView.as_view(), name='budget-alerts'),
    path('spending-patterns/daily-heatmap/', DailySpendingHeatmapView.as_view(), name='daily-heatmap'),
    path('spending-patterns/weekly-breakdown/', WeeklyBreakdownView.as_view(), name='weekly-breakdown'),
    path('spending-patterns/time-based/', TimeBasedAnalysisView.as_view(), name='time-based-analysis'),
    path('category-analysis/comparison/', CategoryComparisonView.as_view(), name='category-comparison'),
    path('category-analysis/trends/', CategoryTrendsView.as_view(), name='category-trends'),
    path('category-analysis/efficiency/', CategoryEfficiencyView.as_view(), name='category-efficiency'),
    path('cash-flow/timeline/', CashFlowTimelineView.as_view(), name='cash-flow-timeline'),
    path('cash-flow/income-vs-expense/', IncomeVsExpenseTimelineView.as_view(), name='income-vs-expense-timeline'),
    path('cash-flow/balance-trend/', BalanceTrendView.as_view(), name='balance-trend'),
    path('insights/spending/', SpendingInsightsView.as_view(), name='spending-insights'),
    path('insights/savings-opportunities/', SavingsOpportunitiesView.as_view(), name='savings-opportunities'),
    path('insights/recurring-expenses/', RecurringExpensesView.as_view(), name='recurring-expenses'),
    path('quick-stats/', QuickStatsView.as_view(), name='quick-stats'),
    path('quick-stats/recommendations/', PriorityRecommendationsView.as_view(), name='priority-recommendations'),
]

