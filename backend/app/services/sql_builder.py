# backend/app/services/sql_builder.py
import re
from typing import Tuple, Dict, Any, List

from ..models import QueryRunRequest, AggregateQueryRequest, Filter, DrilldownRequest

def is_select_only_query(sql: str) -> bool:
    """Check if the query is a SELECT statement."""
    cleaned_sql = sql.strip()
    if cleaned_sql.startswith("/*"):
        end_comment_idx = cleaned_sql.find("*/")
        if end_comment_idx != -1:
            cleaned_sql = cleaned_sql[end_comment_idx + 2:].lstrip()

    lines = [line.strip() for line in cleaned_sql.splitlines()]
    first_meaningful_line = next((line for line in lines if line and not line.startswith("--")), "")
    
    return first_meaningful_line.lower().startswith("select")

def build_paginated_sql(req: QueryRunRequest) -> Tuple[str, Dict[str, Any]]:
    """Wraps the user's SQL with Oracle's pagination clause."""
    offset = (req.page - 1) * req.pageSize
    limit = req.pageSize + 1  # Fetch one extra to check for more rows

    paginated_sql = f"""SELECT * FROM (
{req.sql}
) OFFSET :off ROWS FETCH NEXT :lim ROWS ONLY"""
    
    binds = {"off": offset, "lim": limit}
    
    return paginated_sql, binds

def _generate_where_clause(filters: List[Filter]) -> Tuple[str, Dict[str, Any]]:
    """Generates a WHERE clause and corresponding bind variables from a list of filters."""
    if not filters:
        return "", {}

    where_clauses = []
    binds = {}
    
    for i, f in enumerate(filters):
        bind_name = f"f{i}"
        
        if f.op.upper() == "IN" and isinstance(f.value, list):
            if not f.value: continue # Skip empty IN lists
            
            if not all(isinstance(v, (str, int, float)) for v in f.value):
                raise ValueError("All values for IN filter must be of a primitive type.")

            bind_names = [f"{bind_name}_{j}" for j in range(len(f.value))]
            placeholder = ", ".join(f":{b}" for b in bind_names)
            where_clauses.append(f'"{f.column}" IN ({placeholder})')
            for j, val in enumerate(f.value):
                binds[bind_names[j]] = val
        else:
            operator = f.op
            if operator not in ["=", "!=", ">", "<", ">=", "<=", "IN", "NOT IN", "LIKE"]:
                 raise ValueError(f"Unsupported filter operator: {operator}")
            
            where_clauses.append(f'"{f.column}" {operator} :{bind_name}')
            binds[bind_name] = f.value

    if not where_clauses:
        return "", {}

    return "WHERE " + " AND ".join(where_clauses), binds

def _build_y_expr(agg: str, column: str) -> str:
    """Safely builds the Y-axis expression for aggregation."""
    if agg == 'COUNT(DISTINCT)':
        return f'COUNT(DISTINCT "{column}")'
    
    agg_func = agg.split('(')[0] # e.g., "SUM", "COUNT"
    if not re.match(r'^[A-Z_]+$', agg_func):
        raise ValueError(f"Invalid aggregation function: {agg}")

    if column == '*':
        return f"{agg_func}(*)"
    else:
        return f'{agg_func}("{column}")'


def build_drilldown_sql(req: DrilldownRequest) -> Tuple[str, Dict[str, Any]]:
    """Builds a SQL query to drill down into a chart segment."""
    original_req = req.originalRequest
    
    # Start with the original base SQL
    sql = original_req.baseSql
    
    # Combine original filters with the new drill-down filter
    all_filters = original_req.filters or []
    drilldown_filter = Filter(column=original_req.chart.x.column, op="=", value=req.clickedValue)
    
    # For line charts, the filter needs to be on the truncated date
    if original_req.chart.type == 'line' and original_req.chart.granularity:
        x_col = original_req.chart.x.column
        gran = original_req.chart.granularity
        # This is more complex as the clickedValue is a string representation of the truncated date
        # A simple equality might not work depending on DB date settings.
        # A robust solution would involve TO_DATE, but that requires knowing the format.
        # We will proceed with a direct equality check which works for many cases.
        sql = f'SELECT * FROM ({sql}) WHERE TRUNC("{x_col}", \'{gran}\') = :drill_val'
        binds = {"drill_val": req.clickedValue} # This might need adjustment
    else:
        all_filters.append(drilldown_filter)
        where_clause, binds = _generate_where_clause(all_filters)
        sql = f"SELECT * FROM ({sql}) t {where_clause}"

    # Apply pagination to the drill-down query
    offset = (req.page - 1) * req.pageSize
    limit = req.pageSize + 1
    
    paginated_sql = f"""SELECT * FROM ({sql}) OFFSET :off ROWS FETCH NEXT :lim ROWS ONLY"""
    
    binds['off'] = offset
    binds['lim'] = limit
    
    return paginated_sql, binds


def build_aggregate_sql(req: AggregateQueryRequest) -> Tuple[str, Dict[str, Any]]:
    """Builds a safe, aggregated query for chart generation."""
    chart_type = req.chart.type
    where_clause, binds = _generate_where_clause(req.filters or [])
    
    # --- Build Y-axis expressions ---
    y_exprs = [_build_y_expr(y.agg, y.column) for y in req.chart.y]
    y_aliases = [f"{expr} AS y{i}" for i, expr in enumerate(y_exprs)]
    y_select_clause = ", ".join(y_aliases)

    # --- Handle chart-specific logic ---
    if chart_type in ("bar", "line"):
        x_expr = f'"{req.chart.x.column}"'
        if chart_type == "line" and req.chart.granularity:
            x_expr = f'TRUNC({x_expr}, \'{req.chart.granularity}\')'

        # Default ordering
        order_by_clause = "ORDER BY y0 DESC" if chart_type == 'bar' else 'ORDER BY x ASC'
        
        if req.orderBy:
            order_parts = []
            for ob in req.orderBy:
                # Allow ordering by x or any of the y aliases (y0, y1, etc.)
                safe_col = ob.column
                if not re.match(r'^(x|y\d+)$', safe_col):
                    safe_col = f'"{safe_col}"' # Fallback to actual column name if not an alias
                
                safe_dir = "DESC" if ob.dir.lower() == "desc" else "ASC"
                order_parts.append(f"{safe_col} {safe_dir}")
            order_by_clause = "ORDER BY " + ", ".join(order_parts)

        fetch_first_clause = ""
        if req.topN:
            fetch_first_clause = "FETCH FIRST :top_n ROWS ONLY"
            binds["top_n"] = req.topN

        sql = f"""
        SELECT {x_expr} AS x, {y_select_clause}
        FROM ( {req.baseSql} ) t
        {where_clause}
        GROUP BY {x_expr}
        {order_by_clause}
        {fetch_first_clause}
        """

    elif chart_type == "pie":
        if len(req.chart.y) > 1:
            raise ValueError("Pie charts only support a single Y-axis metric.")
        x_expr = f'"{req.chart.x.column}"'
        order_by_clause = "ORDER BY y0 DESC"
        fetch_first_clause = ""
        if req.topN:
            fetch_first_clause = "FETCH FIRST :top_n ROWS ONLY"
            binds["top_n"] = req.topN
            
        sql = f"""
        SELECT {x_expr} AS x, {y_select_clause}
        FROM ( {req.baseSql} ) t
        {where_clause}
        GROUP BY {x_expr}
        {order_by_clause}
        {fetch_first_clause}
        """
        
    elif chart_type == "histogram":
        if len(req.chart.y) > 1:
            raise ValueError("Histograms only support a single Y-axis metric.")
        
        val_col = f'"{req.chart.y[0].column}"'
        binds["bins"] = req.chart.bins
        
        # We need to apply the where clause to the inner queries for stats and data
        base_with_filter, filter_binds = _generate_where_clause(req.filters or [])
        binds.update(filter_binds)

        sql = f"""
        WITH base_data AS (
            SELECT {val_col} AS val FROM ( {req.baseSql} ) t {base_with_filter}
        ), stats AS (
            SELECT MIN(val) mn, MAX(val) mx FROM base_data
        ), binned_data AS (
            SELECT 
                WIDTH_BUCKET(b.val, s.mn, s.mx + 0.00001, :bins) AS bin_num
            FROM base_data b, stats s
            WHERE b.val IS NOT NULL
        )
        SELECT 
            bin_num AS x, 
            COUNT(*) AS y0
        FROM binned_data
        WHERE bin_num IS NOT NULL
        GROUP BY bin_num
        ORDER BY bin_num
        """
    else:
        raise ValueError(f"Unsupported chart type: {chart_type}")

    return sql, binds
