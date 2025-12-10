from django.urls import path
from .views import (
    DashboardOverviewView,
    IncomeDistributionView,
    ExpenseDistributionView,
    MonthlyChartView
)

urlpatterns = [
    path('overview/', DashboardOverviewView.as_view(), name='dashboard-overview'),
    path('income-distribution/', IncomeDistributionView.as_view(), name='income-distribution'),
    path('expense-distribution/', ExpenseDistributionView.as_view(), name='expense-distribution'),
    path('monthly-chart/', MonthlyChartView.as_view(), name='monthly-chart'),
]




