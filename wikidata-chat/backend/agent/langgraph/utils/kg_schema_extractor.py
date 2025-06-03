# backend/agent/langgraph/utils/kg_schema_extractor.py
from datetime import datetime
import re

def separate_camel_case(s):
    """Separate camel case strings with spaces"""
    separated = re.sub("([a-z])([A-Z])", r"\1 \2", s)
    return separated

def legal_entity_label(url):
    """
    Generate a human-readable label from a legal entity URL
    """
    parts = url.strip("/").split("/")
    transformed_parts = []
    month_mapping = {
        "January": "Januari",
        "February": "Februari",
        "March": "Maret",
        "April": "April",
        "May": "Mei",
        "June": "Juni",
        "July": "Juli",
        "August": "Agustus",
        "September": "September",
        "October": "Oktober",
        "November": "November",
        "December": "Desember",
    }
    for i, part in enumerate(parts):
        if part == "lex2kg":
            transformed_parts = []
            continue
        if part == "uu":
            transformed_parts.append("UU")
        elif part.isdigit() and len(part) <= 2:
            transformed_parts.append(f"no {part}")
        elif part.isdigit() and len(part) == 4 and int(part) >= 1945:
            transformed_parts.append(f"tahun {part}")
        elif part.isdigit() and len(part) == 8:
            try:
                date_obj = datetime.strptime(part, "%Y%m%d")
                formatted_date = date_obj.strftime("%-d %B %Y")
                for eng, indo in month_mapping.items():
                    formatted_date = formatted_date.replace(eng, indo)
                transformed_parts.append(formatted_date)
            except ValueError:
                transformed_parts.append(part)
        elif part.isdigit():
            num = str(int(part))
            transformed_parts.append(num)
        else:
            transformed_parts.append(separate_camel_case(part).lower())
    return " ".join(transformed_parts)

def legal_property_label(x):
    """
    Generate a human-readable label from a legal property
    """
    if "http" in x:
        x = x.split("/")[-1]
    else:
        x = x.split(":")[-1]
    return separate_camel_case(x).lower()

def gesis_entity_label(url):
    """
    Generate a human-readable label from a GESIS entity URL
    """
    if url.startswith("http"):
        parts = url.strip("/").split("/")
        last_part = parts[-1]
        return separate_camel_case(last_part).lower()
    return url

def gesis_property_label(x):
    """
    Generate a human-readable label from a GESIS property
    """
    if "http" in x:
        x = x.split("/")[-1]
    else:
        x = x.split(":")[-1]
    return separate_camel_case(x).lower()
