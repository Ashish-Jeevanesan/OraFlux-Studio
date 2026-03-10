# backend/tests/test_sql_builder.py
import pytest
from uuid import uuid4

from app.services.sql_builder import (
    is_select_only_query,
    build_paginated_sql,
    build_aggregate_sql,
)
from app.models import (
    QueryRunRequest,
    AggregateQueryRequest,
    ChartConfig,
    ChartX,
    ChartY,
    Filter,
)

# --- Tests for is_select_only_query ---

@pytest.mark.parametrize("query, expected", [
    ("SELECT * FROM my_table", True),
    ("select col1, col2 from t", True),
    ("   SELECT * FROM dual", True),
    ("UPDATE my_table SET col1 = 'value'", False),
    ("DELETE FROM my_table", False),
    ("INSERT INTO my_table VALUES (1)", False),
    ("DROP TABLE my_table", False),
    ("""-- a comment
SELECT * FROM t""", True),
    ("/* another comment */ SELECT 1 FROM dual", True),
    ("WITH cte AS (SELECT 1) SELECT * FROM cte", False), # A limitation of the simple checker
])
def test_is_select_only_query(query, expected):
    assert is_select_only_query(query) == expected

# --- Tests for build_paginated_sql ---

def test_build_paginated_sql():
    req = QueryRunRequest(
        sessionId=uuid4(),
        sql="SELECT * FROM test_table WHERE id = 1",
        page=3,
        pageSize=100
    )
    sql, binds = build_paginated_sql(req)
    
    assert "OFFSET :off ROWS FETCH NEXT :lim ROWS ONLY" in sql
    assert binds["off"] == 200
    assert binds["lim"] == 101 # pageSize + 1

# --- Tests for build_aggregate_sql ---

def test_build_aggregate_sql_bar_chart():
    req = AggregateQueryRequest(
        sessionId=uuid4(),
        baseSql="SELECT region, sales FROM monthly_sales",
        chart=ChartConfig(
            type="bar",
            x=ChartX(column="region", role="dimension"),
            y=ChartY(column="sales", agg="SUM", role="measure"),
        ),
        topN=10
    )
    sql, binds = build_aggregate_sql(req)

    assert 'SELECT "region" AS x, SUM("sales") AS y' in sql
    assert 'GROUP BY "region"' in sql
    assert "ORDER BY y DESC" in sql
    assert "FETCH FIRST :top_n ROWS ONLY" in sql
    assert binds["top_n"] == 10

def test_build_aggregate_sql_line_chart_with_filter():
    req = AggregateQueryRequest(
        sessionId=uuid4(),
        baseSql="SELECT order_date, amount FROM orders",
        chart=ChartConfig(
            type="line",
            x=ChartX(column="order_date", role="dimension"),
            y=ChartY(column="amount", agg="AVG", role="measure"),
            granularity="MM"
        ),
        filters=[
            Filter(column="amount", op=">", value=100)
        ]
    )
    sql, binds = build_aggregate_sql(req)
    
    assert 'TRUNC("order_date", \'MM\')' in sql
    assert 'AVG("amount")' in sql
    assert 'FROM ( SELECT order_date, amount FROM orders ) t' in sql
    assert 'WHERE "amount" > :f0' in sql
    assert 'GROUP BY TRUNC("order_date", \'MM\')' in sql
    assert "ORDER BY x ASC" in sql
    assert binds["f0"] == 100

def test_build_aggregate_sql_histogram():
    req = AggregateQueryRequest(
        sessionId=uuid4(),
        baseSql="SELECT user_age FROM demographics",
        chart=ChartConfig(
            type="histogram",
            x=ChartX(column="user_age", role="dimension"), # not used for histo, but required by model
            y=ChartY(column="user_age", agg="COUNT", role="measure"), # y-column is the value to bucket
            bins=15
        )
    )
    sql, binds = build_aggregate_sql(req)

    assert "WITH base_data AS" in sql
    assert "WIDTH_BUCKET" in sql
    assert binds["bins"] == 15
    assert 'SELECT "user_age" AS val' in sql

def test_build_aggregate_sql_count_distinct():
    req = AggregateQueryRequest(
        sessionId=uuid4(),
        baseSql="SELECT country, user_id FROM web_traffic",
        chart=ChartConfig(
            type="bar",
            x=ChartX(column="country", role="dimension"),
            y=ChartY(column="user_id", agg="COUNT(DISTINCT)", role="measure"),
        )
    )
    sql, binds = build_aggregate_sql(req)
    
    assert 'COUNT(DISTINCT "user_id")' in sql

def test_build_aggregate_sql_in_filter():
    req = AggregateQueryRequest(
        sessionId=uuid4(),
        baseSql="SELECT city, population FROM cities",
        chart=ChartConfig(
            type="bar",
            x=ChartX(column="city", role="dimension"),
            y=ChartY(column="population", agg="SUM", role="measure"),
        ),
        filters=[
            Filter(column="country", op="IN", value=["USA", "Canada", "Mexico"])
        ]
    )
    sql, binds = build_aggregate_sql(req)
    
    assert '"country" IN (:f0_0, :f0_1, :f0_2)' in sql
    assert binds["f0_0"] == "USA"
    assert binds["f0_1"] == "Canada"
    assert binds["f0_2"] == "Mexico"
