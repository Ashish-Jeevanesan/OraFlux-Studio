# backend/app/services/intelligent_summary_service.py
import re
import sqlparse
import logging
from typing import Dict, List, Any
from sqlparse.sql import IdentifierList, Identifier
from sqlparse.tokens import Keyword, Name

logger = logging.getLogger(__name__)

def extract_table_names(sql: str) -> List[str]:
    """
    Extracts table names from a SQL query using a regex-based approach.
    This finds words that follow FROM or JOIN clauses.
    """
    regex = r"\s(?:from|join)\s+([a-zA-Z0-9_.]+)"
    tables = re.findall(regex, sql, re.IGNORECASE)
    cleaned_tables = [table.split('.')[-1] for table in tables]
    logger.info(f"Extracted tables from query: {cleaned_tables}")
    return [t.upper() for t in cleaned_tables]

def _find_primary_date_column(schemas: Dict[str, List[Dict[str, Any]]]) -> str:
    """Heuristic to find the best date column for grouping from a schema."""
    if not schemas:
        return None
    # Get the first (and likely only) table's schema
    first_table_schema = next(iter(schemas.values()), [])
    for col in first_table_schema:
        if col['type'] in ('DATE', 'TIMESTAMP'):
            if 'CREATED' in col['name'].upper() or 'DATE' in col['name'].upper():
                return col['name']
    return None

def _find_primary_id_column(schemas: Dict[str, List[Dict[str, Any]]]) -> str:
    """Heuristic to find a primary key from a schema for counting."""
    if not schemas:
        return None
    first_table_schema = next(iter(schemas.values()), [])
    for col in first_table_schema:
        if 'ID' in col['name'].upper():
            return col['name']
    return None

def _generate_report_title(table_names: List[str]) -> str:
    """Creates a simple report title from a list of table names."""
    if not table_names:
        return "Summary Report"
    cleaned_names = [name.replace('_', ' ').title() for name in table_names]
    return " vs ".join(cleaned_names) + " Report"


def generate_summary_sql(base_sql: str, schemas: Dict[str, List[Dict[str, Any]]], granularity: str = "month") -> tuple[str, str]:
    """
    Applies heuristics to the schemas of tables in the base_sql to generate
    a relevant summary SQL query and a report title.
    """
    granularity_map = {
        "month": {"trunc": "MM", "format": "Mon YYYY", "label": "Month"},
        "week": {"trunc": "IW", "format": 'YYYY - "WW"', "label": "Week"},
        "year": {"trunc": "YYYY", "format": "YYYY", "label": "Year"},
    }
    
    if granularity not in granularity_map:
        raise ValueError(f"Unsupported granularity: {granularity}")

    trunc_format = granularity_map[granularity]["trunc"]
    char_format = granularity_map[granularity]["format"]
    label = granularity_map[granularity]["label"]

    table_names = list(schemas.keys())
    report_title = _generate_report_title(table_names)
    
    date_col = _find_primary_date_column(schemas)
    id_col = _find_primary_id_column(schemas)

    if not date_col:
        raise ValueError("Could not determine a primary date column from the query's result columns for summary generation.")

    count_expr = f'COUNT(DISTINCT {id_col})' if id_col else "COUNT(*)"
    
    summary_sql = f"""
        WITH detail_data AS (
            {base_sql}
        )
        SELECT
            TO_CHAR(TRUNC({date_col}, '{trunc_format}'), '{char_format}') AS "{label}",
            {count_expr} AS "Total Records"
        FROM
            detail_data
        WHERE
            {date_col} >= ADD_MONTHS(SYSDATE, -36)
        GROUP BY
            TRUNC({date_col}, '{trunc_format}')
        ORDER BY
            TRUNC({date_col}, '{trunc_format}')
    """
    
    logger.info(f"Generated intelligent summary SQL: {summary_sql}")
    return summary_sql, report_title
