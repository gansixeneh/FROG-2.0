# backend/agent/langgraph/utils/date_utils.py
from datetime import datetime
import re
import logging

logger = logging.getLogger(__name__)

def format_reference_date(date_str):
    """
    Format a reference date string to human-readable format
    
    Args:
        date_str: Date string in various formats (ISO, etc.)
        
    Returns:
        Formatted date string (e.g., "28 July 2018") or original string if parsing fails
    """
    if not date_str or not isinstance(date_str, str):
        return date_str
    
    try:
        # Handle ISO format with timezone (2018-07-28T00:00:00Z)
        if 'T' in date_str:
            # Remove timezone info and parse
            clean_date = date_str.split('T')[0]
            parsed_date = datetime.strptime(clean_date, '%Y-%m-%d')
        # Handle simple date format (2018-07-28)
        elif re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
            parsed_date = datetime.strptime(date_str, '%Y-%m-%d')
        # Handle other common formats
        elif re.match(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$', date_str):
            parsed_date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
        else:
            # If we can't parse it, return the original
            return date_str
        
        # Format as "28 July 2018"
        return parsed_date.strftime('%d %B %Y')
        
    except ValueError as e:
        logger.warning(f"Could not parse date string '{date_str}': {e}")
        return date_str