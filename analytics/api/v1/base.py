"""
Base utilities and mixins for calendar-based analytics views.
Provides reusable functionality for Jalali/Gregorian calendar filtering.
"""
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from base.utils import get_month_range
from drf_spectacular.utils import OpenApiParameter
import jdatetime
from datetime import datetime
from typing import Optional, Tuple, Dict, Any, List


def get_calendar_parameters(description: str = "Calendar filtering parameters"):
    """
    Get standard calendar query parameters for Swagger documentation.
    
    Args:
        description: Custom description for the parameter group (currently unused but kept for future use)
        
    Returns:
        List of OpenApiParameter objects
    """
    return [
        OpenApiParameter(
            name='calendar',
            type=str,
            location=OpenApiParameter.QUERY,
            description='Calendar type: "jalali" or "gregorian"',
            required=False,
            enum=['jalali', 'gregorian'],
            default='gregorian'
        ),
        OpenApiParameter(
            name='month',
            type=str,
            location=OpenApiParameter.QUERY,
            description='Month in format YYYY-MM (e.g., 1403-07 for Jalali or 2024-10 for Gregorian). Defaults to current month.',
            required=False
        ),
        OpenApiParameter(
            name='lang',
            type=str,
            location=OpenApiParameter.QUERY,
            description='Language code: "en" for English or "fa" for Persian/Farsi. Can also be sent via Accept-Language header.',
            required=False,
            enum=['en', 'fa'],
            default='en'
        ),
    ]


def get_calendar_response_schema(additional_properties: Dict[str, Any] = None):
    """
    Get standard calendar response schema for Swagger documentation.
    
    Args:
        additional_properties: Additional properties to include in the response schema
        
    Returns:
        Dict representing the OpenAPI response schema
    """
    base_schema = {
        'type': 'object',
        'properties': {
            'month': {
                'type': 'string',
                'description': 'Month in YYYY-MM format'
            },
            'month_name': {
                'type': 'string',
                'description': 'Formatted month name (e.g., "October 2024" or "مهر 1403")'
            },
            'calendar_type': {
                'type': 'string',
                'enum': ['jalali', 'gregorian'],
                'description': 'Calendar type used for the query'
            },
            'month_range': {
                'type': 'object',
                'properties': {
                    'start': {
                        'type': 'string',
                        'format': 'date',
                        'description': 'Start date of the month range (ISO format)'
                    },
                    'end': {
                        'type': 'string',
                        'format': 'date',
                        'description': 'End date of the month range (ISO format)'
                    }
                }
            }
        }
    }
    
    if additional_properties:
        base_schema['properties'].update(additional_properties)
    
    return base_schema


class CalendarFilterMixin:
    """
    Mixin that provides calendar-based date filtering functionality.
    Can be used with any APIView that needs calendar filtering.
    """
    
    def get_calendar_type(self, request) -> str:
        """
        Extract and validate calendar type from request.
        
        Returns:
            str: 'jalali' or 'gregorian'
            
        Raises:
            ValueError: If calendar type is invalid
        """
        calendar_type = request.query_params.get('calendar', 'gregorian').lower()
        if calendar_type not in ['jalali', 'gregorian']:
            raise ValueError(_('Invalid calendar type. Use "jalali" or "gregorian".'))
        return calendar_type
    
    def get_language(self, request) -> str:
        """
        Extract and validate language from request.
        Language can be set via query parameter 'lang' or Accept-Language header.
        
        Returns:
            str: Language code ('en' or 'fa')
        """
        # Check query parameter first
        language = request.query_params.get('lang') or request.query_params.get('language')
        if language:
            language = language.lower()
            if language in ['en', 'fa']:
                return language
        
        # Fall back to request language (set by middleware)
        from django.utils.translation import get_language
        return get_language() or 'en'
    
    def get_month_param(self, request) -> Optional[str]:
        """
        Extract month parameter from request.
        
        Returns:
            Optional[str]: Month in YYYY-MM format or None
        """
        return request.query_params.get('month')
    
    def get_date_range(self, calendar_type: str, month_param: Optional[str] = None) -> Tuple[datetime, datetime]:
        """
        Get date range (start and end datetime) for the specified calendar month.
        
        Args:
            calendar_type: 'jalali' or 'gregorian'
            month_param: Optional month in YYYY-MM format
            
        Returns:
            Tuple of (start_datetime, end_datetime) as timezone-aware datetimes
        """
        # Get month range based on calendar type
        start_date, end_date = get_month_range(
            calendar_type=calendar_type,
            specific_date=month_param
        )
        
        # Convert to datetime for filtering (include full day range)
        start_datetime = timezone.make_aware(
            datetime.combine(start_date, datetime.min.time())
        )
        end_datetime = timezone.make_aware(
            datetime.combine(end_date, datetime.max.time())
        )
        
        return start_datetime, end_datetime
    
    def get_month_info(self, start_date, calendar_type: str, request=None) -> Dict[str, str]:
        """
        Get formatted month information for response.
        
        Args:
            start_date: datetime.date object
            calendar_type: 'jalali' or 'gregorian'
            request: Optional request object to get language preference
            
        Returns:
            Dict with 'month' (YYYY-MM), 'month_name' (formatted name), and 'calendar_type'
        """
        # Get current language
        from django.utils.translation import get_language
        current_language = get_language() or 'en'
        
        if calendar_type == 'jalali':
            jalali_date = jdatetime.date.fromgregorian(date=start_date)
            month_display = jalali_date.strftime('%Y-%m')
            
            # Jalali month names in Persian
            jalali_months_fa = [
                'فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
                'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند'
            ]
            
            # Jalali month names in English (translatable)
            jalali_months_en = [
                _('Farvardin'), _('Ordibehesht'), _('Khordad'), _('Tir'), 
                _('Mordad'), _('Shahrivar'), _('Mehr'), _('Aban'), 
                _('Azar'), _('Dey'), _('Bahman'), _('Esfand')
            ]
            
            month_index = jalali_date.month - 1
            if current_language == 'fa':
                month_name = f"{jalali_months_fa[month_index]} {jalali_date.year}"
            else:
                month_name = f"{jalali_months_en[month_index]} {jalali_date.year}"
        else:
            month_display = start_date.strftime('%Y-%m')
            # Gregorian months - use strftime which respects locale
            month_name_en = start_date.strftime('%B %Y')
            # For Gregorian, we can use translation if needed
            # For now, use the English format (can be extended with locale)
            month_name = month_name_en
        
        return {
            'month': month_display,
            'month_name': month_name,
            'calendar_type': calendar_type
        }
    
    def get_workspace(self, request):
        """
        Get workspace from request (set by middleware).
        
        Returns:
            Workspace object or None
            
        Raises:
            ValueError: If no workspace is selected
        """
        workspace = getattr(request, 'workspace', None)
        if not workspace:
            raise ValueError(_('No workspace selected.'))
        return workspace


def get_all_descendants(category) -> List:
    """
    Get all descendant categories (children, grandchildren, etc.) including the category itself.
    
    Args:
        category: The Category object to get descendants for
        
    Returns:
        List of Category objects including the category itself and all its descendants
    """
    from categories.models import Category
    
    descendants = [category]
    
    def get_children_recursive(parent):
        children = Category.objects.filter(parent=parent)
        for child in children:
            descendants.append(child)
            get_children_recursive(child)
    
    get_children_recursive(category)
    return descendants

