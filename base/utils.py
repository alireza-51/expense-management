from datetime import datetime, date, timedelta
from django.conf import settings
import jdatetime

# Debug function to check what's happening
def debug_language_settings(language_code=None):
    """Debug function to check language and calendar settings"""
    print(f"Debug - Language code: {language_code}")
    print(f"Debug - USE_JALALI_CALENDAR: {getattr(settings, 'USE_JALALI_CALENDAR', False)}")
    print(f"Debug - LANGUAGE_CODE: {getattr(settings, 'LANGUAGE_CODE', 'en')}")
    return language_code


def get_month_range(calendar_type=None, month_offset=0, specific_date=None):
    """
    Get month range based on calendar type and offset.
    
    Args:
        calendar_type: The calendar type ('jalali' or 'gregorian')
        month_offset: Number of months to offset (0=current, -1=previous, 1=next)
        specific_date: Specific date string in format 'YYYY-MM' or 'YYYY-MM-DD'
    
    Returns:
        tuple: (start_date, end_date) in datetime.date format
    """
    if calendar_type is None:
        calendar_type = getattr(settings, 'CALENDAR_TYPE', 'gregorian')
    
    # Use calendar type to determine which calendar to use
    if calendar_type == 'jalali':
        return _get_jalali_month_range(month_offset, specific_date)
    else:
        return _get_gregorian_month_range(month_offset, specific_date)


def get_current_month_range(calendar_type=None):
    """
    Get the current month range based on calendar type setting.
    
    Args:
        calendar_type: The calendar type ('jalali' or 'gregorian')
    
    Returns:
        tuple: (start_date, end_date) in datetime.date format
    """
    return get_month_range(calendar_type, 0)


def _get_jalali_month_range(month_offset=0, specific_date=None):
    """Get Jalali month range with optional offset"""
    if specific_date:
        # Parse specific date
        if len(specific_date) == 7:  # YYYY-MM format
            year, month = map(int, specific_date.split('-'))
            target_date = jdatetime.date(year, month, 1)
        else:  # YYYY-MM-DD format
            year, month, day = map(int, specific_date.split('-'))
            target_date = jdatetime.date(year, month, day)
    else:
        # Use current date with offset
        today = jdatetime.date.today()
        target_date = today
    
    # Apply month offset
    if month_offset != 0:
        # Calculate target month and year
        target_month = target_date.month + month_offset
        target_year = target_date.year
        
        # Handle year rollover
        while target_month > 12:
            target_month -= 12
            target_year += 1
        while target_month < 1:
            target_month += 12
            target_year -= 1
        
        target_date = jdatetime.date(target_year, target_month, 1)
    
    # Get start and end of month
    start_date = jdatetime.date(target_date.year, target_date.month, 1)
    
    # Get the last day of the month
    if start_date.month == 12:
        end_date = jdatetime.date(start_date.year + 1, 1, 1) - jdatetime.timedelta(days=1)
    else:
        end_date = jdatetime.date(start_date.year, start_date.month + 1, 1) - jdatetime.timedelta(days=1)
    
    # Convert to Gregorian for database queries
    start_gregorian = start_date.togregorian()
    end_gregorian = end_date.togregorian()
    
    return start_gregorian, end_gregorian


def _get_gregorian_month_range(month_offset=0, specific_date=None):
    """Get Gregorian month range with optional offset"""
    if specific_date:
        # Parse specific date
        if len(specific_date) == 7:  # YYYY-MM format
            year, month = map(int, specific_date.split('-'))
            target_date = date(year, month, 1)
        else:  # YYYY-MM-DD format
            year, month, day = map(int, specific_date.split('-'))
            target_date = date(year, month, day)
    else:
        # Use current date with offset
        today = date.today()
        target_date = today
    
    # Apply month offset
    if month_offset != 0:
        # Calculate target month and year
        target_month = target_date.month + month_offset
        target_year = target_date.year
        
        # Handle year rollover
        while target_month > 12:
            target_month -= 12
            target_year += 1
        while target_month < 1:
            target_month += 12
            target_year -= 1
        
        target_date = date(target_year, target_month, 1)
    
    # Get start and end of month
    start_date = date(target_date.year, target_date.month, 1)
    
    # Get the last day of the month
    if start_date.month == 12:
        end_date = date(start_date.year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(start_date.year, start_date.month + 1, 1) - timedelta(days=1)
    
    return start_date, end_date


def format_date_for_display(date_obj, calendar_type=None):
    """
    Format a date for display based on calendar type setting.
    
    Args:
        date_obj: datetime.date object
        calendar_type: The calendar type ('jalali' or 'gregorian')
    
    Returns:
        str: Formatted date string
    """
    if calendar_type is None:
        calendar_type = getattr(settings, 'CALENDAR_TYPE', 'gregorian')
    
    if calendar_type == 'jalali':
        # Convert to Jalali and format
        jalali_date = jdatetime.date.fromgregorian(date=date_obj)
        return jalali_date.strftime('%m/%d')
    else:
        # Use Gregorian format
        return date_obj.strftime('%m/%d')


def get_month_title(calendar_type=None, month_offset=0, specific_date=None):
    """
    Get month title based on calendar type setting and offset.
    
    Args:
        calendar_type: The calendar type ('jalali' or 'gregorian')
        month_offset: Number of months to offset (0=current, -1=previous, 1=next)
        specific_date: Specific date string in format 'YYYY-MM' or 'YYYY-MM-DD'
    
    Returns:
        str: Month title
    """
    if calendar_type is None:
        calendar_type = getattr(settings, 'CALENDAR_TYPE', 'gregorian')
    
    print(f"Debug - Calendar type: {calendar_type}, offset: {month_offset}")
    
    if calendar_type == 'jalali':
        if specific_date:
            # Parse specific date
            if len(specific_date) == 7:  # YYYY-MM format
                year, month = map(int, specific_date.split('-'))
                target_date = jdatetime.date(year, month, 1)
            else:  # YYYY-MM-DD format
                year, month, day = map(int, specific_date.split('-'))
                target_date = jdatetime.date(year, month, day)
        else:
            # Use current date with offset
            today = jdatetime.date.today()
            target_date = today
            
            # Apply month offset
            if month_offset != 0:
                target_month = target_date.month + month_offset
                target_year = target_date.year
                
                # Handle year rollover
                while target_month > 12:
                    target_month -= 12
                    target_year += 1
                while target_month < 1:
                    target_month += 12
                    target_year -= 1
                
                target_date = jdatetime.date(target_year, target_month, 1)
        
        jalali_months = [
            'فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
            'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند'
        ]
        month_name = jalali_months[target_date.month - 1]
        print(f"Debug - Jalali month: {month_name} (month {target_date.month})")
        return month_name
    else:
        if specific_date:
            # Parse specific date
            if len(specific_date) == 7:  # YYYY-MM format
                year, month = map(int, specific_date.split('-'))
                target_date = date(year, month, 1)
            else:  # YYYY-MM-DD format
                year, month, day = map(int, specific_date.split('-'))
                target_date = date(year, month, day)
        else:
            # Use current date with offset
            today = date.today()
            target_date = today
            
            # Apply month offset
            if month_offset != 0:
                target_month = target_date.month + month_offset
                target_year = target_date.year
                
                # Handle year rollover
                while target_month > 12:
                    target_month -= 12
                    target_year += 1
                while target_month < 1:
                    target_month += 12
                    target_year -= 1
                
                target_date = date(target_year, target_month, 1)
        
        gregorian_months = [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ]
        month_name = gregorian_months[target_date.month - 1]
        print(f"Debug - Gregorian month: {month_name} (month {target_date.month})")
        return month_name 