"""
Base utilities and mixins for calendar-based analytics views.
Provides reusable functionality for Jalali/Gregorian calendar filtering.
"""
from django.utils import timezone
from base.utils import get_month_range
from drf_spectacular.utils import OpenApiParameter
import jdatetime
from datetime import datetime
from typing import Optional, Tuple, Dict, Any


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
            raise ValueError('Invalid calendar type. Use "jalali" or "gregorian".')
        return calendar_type
    
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
    
    def get_month_info(self, start_date, calendar_type: str) -> Dict[str, str]:
        """
        Get formatted month information for response.
        
        Args:
            start_date: datetime.date object
            calendar_type: 'jalali' or 'gregorian'
            
        Returns:
            Dict with 'month' (YYYY-MM), 'month_name' (formatted name), and 'calendar_type'
        """
        if calendar_type == 'jalali':
            jalali_date = jdatetime.date.fromgregorian(date=start_date)
            month_display = jalali_date.strftime('%Y-%m')
            month_name = jalali_date.strftime('%B %Y')
        else:
            month_display = start_date.strftime('%Y-%m')
            month_name = start_date.strftime('%B %Y')
        
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
            raise ValueError('No workspace selected.')
        return workspace

