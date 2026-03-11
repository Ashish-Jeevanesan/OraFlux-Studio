# backend/app/services/intelligent_summary_service.py
import re
import sqlparse
import logging
from typing import Dict, List, Any
from sqlparse.sql import IdentifierList, Identifier
from sqlparse.tokens import Keyword, Name

logger = logging.getLogger(__name__)

def _get_result_columns(sql: str) -> List[str]:
    """
    Parses a SQL query and returns a list of the final column names,
    respecting aliases.
    """
    parsed = sqlparse.parse(sql)[0]
    
    # Find the first SELECT statement's tokens
    select_tokens = []
    from_seen = False
    for token in parsed.tokens:
        if token.ttype is Keyword and token.value.upper() == 'FROM':
            from_seen = True
            break
        select_tokens.append(token)

    if not from_seen:
        return []

    # Process the tokens between SELECT and FROM
    columns = []
    for token in select_tokens:
        if isinstance(token, IdentifierList):
            for identifier in token.get_identifiers():
                columns.append(identifier.get_alias() or identifier.get_real_name())
        elif isinstance(token, Identifier):
            columns.append(token.get_alias() or token.get_real_name())
        elif token.ttype is Name:
            columns.append(token.value)
            
    # The above can be messy, a simple split on ',' is often more reliable for simple queries
    if not columns and parsed.get_type() == 'SELECT':
        # Get the text between SELECT and FROM
        select_part = ''.join(str(t) for t in select_tokens).strip()
        if select_part.upper().startswith('SELECT'):
            select_part = select_part[6:].strip()
        
        # Naive split and clean
        for col_str in select_part.split(','):
            col_str = col_str.strip()
            # Try to find alias
            if ' as ' in col_str.lower():
                alias = col_str.split(' as ')[-1]
                columns.append(alias.strip().replace('"', ''))
            else:
                # Take the last word, which is often the alias or column name
                columns.append(col_str.split()[-1].replace('"', ''))

    logger.info(f"Extracted result columns: {columns}")
    return columns


def _find_primary_date_column(result_columns: List[str]) -> str:
    """Heuristic to find the best date column from a list of result columns."""
    for col in result_columns:
        if 'DATE' in col.upper() or 'CREATED' in col.upper():
            return col
    return None

def _find_primary_id_column(result_columns: List[str]) -> str:
    """Heuristic to find a primary key from a list of result columns."""
    for col in result_columns:
        if 'ID' in col.upper():
            return col
    return None

def _generate_report_title_from_sql(sql: str) -> str:
    """Creates a simple report title by extracting table names with a regex."""
    regex = r"\s(?:from|join)\s+([a-zA-Z0-9_.]+)"
    tables = re.findall(regex, sql, re.IGNORECASE)
    cleaned_names = [table.split('.')[-1].replace('_', ' ').title() for table in tables]
    if not cleaned_names:
        return "Summary Report"
    return " vs ".join(cleaned_names) + " Report"


def generate_summary_sql(base_sql: str) -> tuple[str, str]:
    """
    Applies heuristics to the result columns of the base_sql to generate
    a relevant summary SQL query and a report title.
    Returns a tuple of (summary_sql, report_title).
    """
    
    # --- Generate Title ---
    report_title = _generate_report_title_from_sql(base_sql)
    
    # --- Parse SQL to find result columns ---
    result_columns = _get_result_columns(base_sql)
    if not result_columns:
        raise ValueError("Could not parse the columns from the SELECT statement.")

    # --- Apply Heuristics to Result Columns ---
    date_col = _find_primary_date_column(result_columns)
    id_col = _find_primary_id_column(result_columns)

    if not date_col:
        raise ValueError("Could not determine a primary date column from the query's result columns for summary generation.")

    # --- Build Summary Query ---
    count_expr = f'COUNT(DISTINCT {id_col})' if id_col else "COUNT(*)"
    
    summary_sql = f"""
        WITH detail_data AS (
            {base_sql}
        )
        SELECT
            TO_CHAR(TRUNC({date_col}, 'MM'), 'Mon YYYY') AS "Month",
            {count_expr} AS "Total Records"
        FROM
            detail_data
        WHERE
            {date_col} >= ADD_MONTHS(SYSDATE, -6)
        GROUP BY
            TRUNC({date_col}, 'MM')
        ORDER BY
            TRUNC({date_col}, 'MM')
    """
    
    logger.info(f"Generated intelligent summary SQL: {summary_sql}")
    return summary_sql, report_title
