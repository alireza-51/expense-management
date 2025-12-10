from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as django_filters
from rest_framework import viewsets, permissions, filters
from django.utils import timezone
from categories.models import Category
from expenses.models import Income, Expense
from .serializers import IncomeSerializer, ExpenseSerializer
from drf_spectacular.utils import extend_schema
import jdatetime
from datetime import datetime


class JalaliDateFilter(django_filters.Filter):
    """Custom filter to handle Jalali date strings and convert to Gregorian"""
    
    def filter(self, qs, value):
        if not value:
            return qs
        
        try:
            # Parse Jalali date (format: YYYY-MM-DD or YYYY-MM-DD HH:MM)
            if ' ' in value or 'T' in value:
                # Has time component
                if 'T' in value:
                    date_str, time_str = value.split('T')
                    time_str = time_str.split('+')[0].split('-')[0]  # Remove timezone
                    if ':' in time_str:
                        hour, minute = map(int, time_str.split(':'))
                    else:
                        hour, minute = int(time_str[:2]), int(time_str[2:4]) if len(time_str) >= 4 else 0
                else:
                    date_str, time_str = value.split(' ')
                    hour, minute = map(int, time_str.split(':'))
                
                year, month, day = map(int, date_str.split('-'))
                jalali_date = jdatetime.datetime(year, month, day, hour, minute)
                gregorian_datetime = jalali_date.togregorian()
            else:
                # Date only - use appropriate time based on lookup expression
                year, month, day = map(int, value.split('-'))
                jalali_date = jdatetime.date(year, month, day)
                gregorian_date = jalali_date.togregorian()
                
                # For 'gte' (from), use start of day; for 'lte' (to), use end of day
                lookup = self.lookup_expr or 'exact'
                if lookup == 'lte':
                    # For 'to' dates, include the entire day
                    gregorian_datetime = datetime.combine(gregorian_date, datetime.max.time())
                else:
                    # For 'from' dates or exact, use start of day
                    gregorian_datetime = datetime.combine(gregorian_date, datetime.min.time())
            
            # Make timezone-aware
            gregorian_datetime = timezone.make_aware(gregorian_datetime)
            
            # Apply the filter based on lookup expression
            return qs.filter(**{f'{self.field_name}__{lookup}': gregorian_datetime})
        except (ValueError, AttributeError, TypeError) as e:
            # If parsing fails, return original queryset
            return qs


class TransactionFilter(django_filters.FilterSet):
    """Base filter for Transaction models (Income/Expense)"""
    category = django_filters.NumberFilter(field_name='category__id', lookup_expr='exact')
    category_name = django_filters.CharFilter(field_name='category__name', lookup_expr='icontains')
    amount_min = django_filters.NumberFilter(field_name='amount', lookup_expr='gte')
    amount_max = django_filters.NumberFilter(field_name='amount', lookup_expr='lte')
    
    # Gregorian date filters
    date_from = django_filters.DateTimeFilter(field_name='transacted_at', lookup_expr='gte')
    date_to = django_filters.DateTimeFilter(field_name='transacted_at', lookup_expr='lte')
    
    # Jalali date filters
    jalali_date_from = JalaliDateFilter(field_name='transacted_at', lookup_expr='gte', 
                                        help_text='Jalali date in format YYYY-MM-DD or YYYY-MM-DD HH:MM')
    jalali_date_to = JalaliDateFilter(field_name='transacted_at', lookup_expr='lte',
                                      help_text='Jalali date in format YYYY-MM-DD or YYYY-MM-DD HH:MM')
    
    # Year and month filters (works for both calendars via calendar parameter)
    # Note: These work on Gregorian dates by default. Use calendar=jalali with these for Jalali filtering.
    year = django_filters.NumberFilter(field_name='transacted_at', lookup_expr='year', method='filter_year_month')
    month = django_filters.NumberFilter(field_name='transacted_at', lookup_expr='month', method='filter_year_month')
    
    def filter_year_month(self, queryset, name, value):
        """Filter by year/month, handling both Gregorian and Jalali calendars"""
        # Get calendar parameter
        calendar = self.data.get('calendar', 'gregorian').lower()
        
        if calendar == 'jalali':
            # For Jalali, skip standard filtering here - we'll handle it in filter_queryset
            # Return queryset unchanged, actual filtering happens in filter_queryset
            return queryset
        else:
            # For Gregorian, use standard filtering
            lookup = f'{name}__year' if name == 'year' else f'{name}__month'
            return queryset.filter(**{lookup: value})
    
    def filter_queryset(self, queryset):
        """Override to handle calendar parameter for year/month filters"""
        # Get calendar and year/month before applying base filters
        calendar = self.data.get('calendar', 'gregorian').lower()
        jalali_year = self.data.get('year')
        jalali_month = self.data.get('month')
        
        # Create a copy of data without year/month for base filtering if Jalali
        if calendar == 'jalali' and (jalali_year or jalali_month):
            # Create mutable copy
            mutable_data = self.data.copy()
            if 'year' in mutable_data:
                mutable_data.pop('year')
            if 'month' in mutable_data:
                mutable_data.pop('month')
            original_data = self.data
            self.data = mutable_data
        
        # Apply base filters
        queryset = super().filter_queryset(queryset)
        
        # Restore original data if we modified it
        if calendar == 'jalali' and (jalali_year or jalali_month):
            self.data = original_data
        
        # If calendar is jalali and year/month are provided, convert to Gregorian date range
        if calendar == 'jalali' and (jalali_year or jalali_month):
            try:
                # Use provided year/month or current Jalali date
                if jalali_year and jalali_month:
                    # Specific Jalali month
                    jalali_start = jdatetime.date(int(jalali_year), int(jalali_month), 1)
                    # Get last day of month
                    if int(jalali_month) == 12:
                        jalali_end = jdatetime.date(int(jalali_year) + 1, 1, 1) - jdatetime.timedelta(days=1)
                    else:
                        jalali_end = jdatetime.date(int(jalali_year), int(jalali_month) + 1, 1) - jdatetime.timedelta(days=1)
                elif jalali_year:
                    # Entire Jalali year
                    jalali_start = jdatetime.date(int(jalali_year), 1, 1)
                    # Get last day of year (Esfand 29 or 30)
                    try:
                        jalali_end = jdatetime.date(int(jalali_year) + 1, 1, 1) - jdatetime.timedelta(days=1)
                    except:
                        jalali_end = jdatetime.date(int(jalali_year), 12, 29)
                else:
                    # Only month provided, use current year
                    today = jdatetime.date.today()
                    jalali_start = jdatetime.date(today.year, int(jalali_month), 1)
                    if int(jalali_month) == 12:
                        jalali_end = jdatetime.date(today.year + 1, 1, 1) - jdatetime.timedelta(days=1)
                    else:
                        jalali_end = jdatetime.date(today.year, int(jalali_month) + 1, 1) - jdatetime.timedelta(days=1)
                
                # Convert to Gregorian
                gregorian_start = datetime.combine(jalali_start.togregorian(), datetime.min.time())
                gregorian_end = datetime.combine(jalali_end.togregorian(), datetime.max.time())
                
                # Make timezone-aware
                gregorian_start = timezone.make_aware(gregorian_start)
                gregorian_end = timezone.make_aware(gregorian_end)
                
                # Apply date range filter
                queryset = queryset.filter(
                    transacted_at__gte=gregorian_start,
                    transacted_at__lte=gregorian_end
                )
            except (ValueError, TypeError):
                # If conversion fails, ignore the filter
                pass
        
        return queryset
    
    class Meta:
        model = None  # Will be set in subclasses
        fields = ['category', 'amount_min', 'amount_max', 'date_from', 'date_to', 
                  'jalali_date_from', 'jalali_date_to', 'year', 'month']


class IncomeFilter(TransactionFilter):
    class Meta:
        model = Income
        fields = ['category', 'amount_min', 'amount_max', 'date_from', 'date_to', 
                  'jalali_date_from', 'jalali_date_to', 'year', 'month']


class ExpenseFilter(TransactionFilter):
    class Meta:
        model = Expense
        fields = ['category', 'amount_min', 'amount_max', 'date_from', 'date_to', 
                  'jalali_date_from', 'jalali_date_to', 'year', 'month']


class BaseTransactionViewSet(viewsets.ModelViewSet):
    """
    Base ViewSet for filtering by workspace and setting created_by/workspace automatically.
    """
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter]
    search_fields = ['category__name', 'notes']
    ordering_fields = ['transacted_at', 'amount', 'created_at', 'category__name']
    ordering = ['-transacted_at']

    def get_queryset(self):
        workspace = getattr(self.request, 'workspace', None)
        return self.queryset.filter(workspace=workspace).select_related('category')

    def perform_create(self, serializer):
        serializer.save(
            workspace=getattr(self.request, 'workspace', None),
            created_by=self.request.user
        )


@extend_schema(tags=["Income"])
class IncomeViewSet(BaseTransactionViewSet):
    queryset = Income.objects.filter(category__type=Category.CategoryType.INCOME)
    serializer_class = IncomeSerializer
    filterset_class = IncomeFilter


@extend_schema(tags=["Expense"])
class ExpenseViewSet(BaseTransactionViewSet):
    queryset = Expense.objects.filter(category__type=Category.CategoryType.EXPENSE)
    serializer_class = ExpenseSerializer
    filterset_class = ExpenseFilter
