# backend/app/services/analytics_service.py
import logging
import asyncio
from typing import Dict, Any, List

from . import intelligent_summary_service as summary_service
from .oracle_service import OracleService

logger = logging.getLogger(__name__)

# --- Report Blueprints ---

class ReportBlueprint:
    """Base class for an analytics blueprint."""
    def get_kpis(self, base_sql: str, schema: Dict[str, Any]) -> List[Dict[str, Any]]:
        return []

    def get_charts(self, base_sql: str, schema: Dict[str, Any]) -> List[Dict[str, Any]]:
        return []

class ShippingInfoBlueprint(ReportBlueprint):
    """Blueprint for queries involving shipping information."""
    
    def get_kpis(self, base_sql: str, schema: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [
            {"name": "Total Shipped Orders", "sql": f"SELECT COUNT(DISTINCT orderid) FROM ({base_sql}) WHERE status = '40'"},
            {"name": "Total Items Shipped", "sql": f"SELECT SUM(itemqty) FROM ({base_sql}) WHERE status = '40'"},
            {"name": "Unique Accounts", "sql": f"SELECT COUNT(DISTINCT accountid) FROM ({base_sql})"},
            {"name": "Unique Parts", "sql": f"SELECT COUNT(DISTINCT partnumber) FROM ({base_sql})"},
        ]

    def get_charts(self, base_sql: str, schema: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [
            {
                "name": "Items by Company",
                "type": "bar",
                "sql": f"SELECT companyname, SUM(itemqty) FROM ({base_sql}) GROUP BY companyname ORDER BY SUM(itemqty) DESC FETCH FIRST 10 ROWS ONLY"
            },
            {
                "name": "Items by Part Family",
                "type": "pie",
                "sql": f"SELECT partfamily, SUM(itemqty) FROM ({base_sql}) GROUP BY partfamily ORDER BY SUM(itemqty) DESC FETCH FIRST 7 ROWS ONLY"
            },
            {
                "name": "Shipping Volume by Date",
                "type": "line",
                "sql": f"SELECT shippeddate, SUM(itemqty) FROM ({base_sql}) WHERE shippeddate IS NOT NULL GROUP BY shippeddate ORDER BY shippeddate ASC"
            },
            {
                "name": "Items by Part Owner",
                "type": "pie",
                "sql": f"SELECT partownername, SUM(itemqty) FROM ({base_sql}) GROUP BY partownername ORDER BY SUM(itemqty) DESC FETCH FIRST 7 ROWS ONLY"
            },
        ]

class OrderBlueprint(ReportBlueprint):
    """Blueprint for queries involving T501_ORDER."""
    def get_kpis(self, base_sql: str, schema: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [
            {"name": "Total Orders", "sql": f"SELECT COUNT(DISTINCT c501_order_id) FROM ({base_sql})"},
            {"name": "Total Order Value", "sql": f"SELECT SUM(c501_total_cost) FROM ({base_sql})"},
            {"name": "Unique Customers", "sql": f"SELECT COUNT(DISTINCT c704_account_id) FROM ({base_sql})"},
        ]
    def get_charts(self, base_sql: str, schema: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [
            {"name": "Order Value by Month", "type": "bar", "sql": f"SELECT TO_CHAR(c501_order_date, 'YYYY-MM'), SUM(c501_total_cost) FROM ({base_sql}) GROUP BY TO_CHAR(c501_order_date, 'YYYY-MM') ORDER BY 1 DESC FETCH FIRST 12 ROWS ONLY"},
            {"name": "Top 10 Customers by Order Value", "type": "pie", "sql": f"SELECT a.c704_account_nm || ' (' || t.c704_account_id || ')', SUM(t.c501_total_cost) FROM ({base_sql}) t LEFT JOIN t704_account a ON t.c704_account_id = a.c704_account_id GROUP BY a.c704_account_nm, t.c704_account_id ORDER BY 2 DESC FETCH FIRST 10 ROWS ONLY"},
        ]

class InvoiceBlueprint(ReportBlueprint):
    """Blueprint for queries involving T503_INVOICE."""
    def get_kpis(self, base_sql: str, schema: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [
            {"name": "Total Invoices", "sql": f"SELECT COUNT(DISTINCT c503_invoice_id) FROM ({base_sql})"},
            {"name": "Total Invoiced Amount", "sql": f"SELECT SUM(c503_inv_amt) FROM ({base_sql})"},
            {"name": "Total Payments Received", "sql": f"SELECT SUM(c503_inv_pymnt_amt) FROM ({base_sql})"},
        ]
    def get_charts(self, base_sql: str, schema: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [
            {"name": "Invoice Amount by Month", "type": "bar", "sql": f"SELECT TO_CHAR(c503_invoice_date, 'YYYY-MM'), SUM(c503_inv_amt) FROM ({base_sql}) GROUP BY TO_CHAR(c503_invoice_date, 'YYYY-MM') ORDER BY 1 DESC FETCH FIRST 12 ROWS ONLY"},
            {"name": "Top 10 Customers by Invoice Amount", "type": "pie", "sql": f"SELECT a.c704_account_nm || ' (' || t.c704_account_id || ')', SUM(t.c503_inv_amt) FROM ({base_sql}) t LEFT JOIN t704_account a ON t.c704_account_id = a.c704_account_id GROUP BY a.c704_account_nm, t.c704_account_id ORDER BY 2 DESC FETCH FIRST 10 ROWS ONLY"},
        ]

class ConsignmentBlueprint(ReportBlueprint):
    """Blueprint for queries involving T504_CONSIGNMENT."""
    def get_kpis(self, base_sql: str, schema: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [
            {"name": "Total Consignments", "sql": f"SELECT COUNT(DISTINCT c504_consignment_id) FROM ({base_sql})"},
            {"name": "Total Consignment Value", "sql": f"SELECT SUM(c504_total_cost) FROM ({base_sql})"},
        ]
    def get_charts(self, base_sql: str, schema: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [
            {"name": "Consignment Value by Ship Date", "type": "bar", "sql": f"SELECT TO_CHAR(c504_ship_date, 'YYYY-MM'), SUM(c504_total_cost) FROM ({base_sql}) GROUP BY TO_CHAR(c504_ship_date, 'YYYY-MM') ORDER BY 1 DESC FETCH FIRST 12 ROWS ONLY"},
            {"name": "Top 10 Distributors by Consignment Value", "type": "pie", "sql": f"SELECT c701_distributor_id, SUM(c504_total_cost) FROM ({base_sql}) GROUP BY c701_distributor_id ORDER BY 2 DESC FETCH FIRST 10 ROWS ONLY"},
        ]


# --- Blueprint Registry ---

BLUEPRINT_REGISTRY = {
    "T907_SHIPPING_INFO": ShippingInfoBlueprint(),
    "T501_ORDER": OrderBlueprint(),
    "T503_INVOICE": InvoiceBlueprint(),
    "T504_CONSIGNMENT": ConsignmentBlueprint(),
}

def _select_blueprint(tables: List[str]) -> ReportBlueprint:
    """Selects the best blueprint based on the tables in the query."""
    for table, blueprint in BLUEPRINT_REGISTRY.items():
        if table in tables:
            logger.info(f"Selected blueprint for table: {table}")
            return blueprint
    return None

# --- Main Service ---

def _apply_date_filter(sql: str, date_col: str) -> str:
    """Injects a 5-year date filter into a SQL query."""
    if not date_col:
        return sql
    
    date_condition = f"{date_col} >= ADD_MONTHS(SYSDATE, -60)"
    
    # Check if a WHERE clause already exists
    if ' where ' in sql.lower():
        # This is a simple append, a more robust solution would parse the SQL
        return f"{sql} AND {date_condition}"
    else:
        return f"{sql} WHERE {date_condition}"

class AnalyticsService:
    def __init__(self, oracle_service: OracleService):
        self._oracle_service = oracle_service

    async def generate_dashboard(self, base_sql: str, session_id: Any, filter_last_5_years: bool) -> Dict[str, Any]:
        """
        Analyzes a query, selects a blueprint, and generates data for a full dashboard.
        """
        # 1. Analyze the query to find tables
        tables = summary_service.extract_table_names(base_sql)
        if not tables:
            raise ValueError("Could not extract any tables from the provided SQL query.")

        # 2. Select the appropriate blueprint
        blueprint = _select_blueprint(tables)
        if not blueprint:
            raise ValueError(f"No analytics blueprint found for the tables in this query: {tables}")

        # 3. Get schema to find date column for filtering
        schema = await self._oracle_service.get_table_schemas(session_id, tables)
        
        # 4. Apply date filter if requested
        filtered_sql = base_sql
        if filter_last_5_years:
            date_col = summary_service._find_primary_date_column(schema)
            if date_col:
                filtered_sql = _apply_date_filter(base_sql, date_col)
                logger.info(f"Applied 5-year filter on column '{date_col}'.")
            else:
                logger.warning("Could not apply 5-year filter: no suitable date column found.")

        # 5. Get the query definitions from the blueprint, using the (potentially filtered) SQL
        kpi_defs = blueprint.get_kpis(filtered_sql, schema)
        chart_defs = blueprint.get_charts(filtered_sql, schema)

        # 6. Execute all queries concurrently
        logger.info(f"Executing {len(kpi_defs)} KPI queries and {len(chart_defs)} chart queries.")
        
        kpi_tasks = []
        for kpi in kpi_defs:
            logger.info(f"KPI Query [{kpi['name']}]: {kpi['sql']}")
            kpi_tasks.append(self._oracle_service.execute_query(session_id, kpi['sql'], {}, 120))
            
        chart_tasks = []
        for chart in chart_defs:
            logger.info(f"Chart Query [{chart['name']}]: {chart['sql']}")
            chart_tasks.append(self._oracle_service.execute_query(session_id, chart['sql'], {}, 120))
        
        results = await asyncio.gather(*(kpi_tasks + chart_tasks))
        
        kpi_results = results[:len(kpi_defs)]
        chart_results = results[len(kpi_defs):]

        # 7. Format the response
        dashboard_data = {
            "title": f"Analytics for {', '.join(tables)}",
            "kpis": [],
            "charts": [],
        }

        for i, kpi_def in enumerate(kpi_defs):
            # Assuming KPI query returns a single value
            value = kpi_results[i]['rows'][0][0] if kpi_results[i]['rows'] else 'N/A'
            dashboard_data['kpis'].append({"name": kpi_def['name'], "value": value})

        for i, chart_def in enumerate(chart_defs):
            dashboard_data['charts'].append({
                "name": chart_def['name'],
                "type": chart_def['type'],
                "data": chart_results[i] # This will contain { columns, rows }
            })
            
        return dashboard_data
