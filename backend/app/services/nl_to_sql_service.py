# backend/app/services/nl_to_sql_service.py
import logging
import re
import asyncio
import os
from typing import Dict, Any, List

import google.generativeai as genai
from . import intelligent_summary_service as summary_service
from .oracle_service import OracleService

logger = logging.getLogger(__name__)

# --- LLM Configuration ---
try:
    # Get the API key from an environment variable
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY environment variable not set.")
    genai.configure(api_key=GEMINI_API_KEY)
    llm_model = genai.GenerativeModel('gemini-pro')
    logger.info("Successfully configured Gemini API.")
except Exception as e:
    logger.error(f"Failed to configure Gemini API: {e}")
    llm_model = None

def _get_relevant_tables(text: str, all_tables: List[str]) -> List[str]:
    """Finds which known tables are mentioned in the user's text."""
    found_tables = []
    text_upper = text.upper()
    for table in all_tables:
        table_name_only = table.split('_', 1)[-1]
        if table_name_only in text_upper:
            found_tables.append(table)
    if not found_tables:
        if "ORDER" in text_upper:
            found_tables.append("T501_ORDER")
        if "INVOICE" in text_upper:
            found_tables.append("T503_INVOICE")
    logger.info(f"Found relevant tables in text: {found_tables}")
    return found_tables

def _format_schema_for_prompt(schemas: Dict[str, List[Dict[str, Any]]]) -> str:
    """Formats the table schemas into a string for the LLM prompt."""
    prompt_str = "Oracle database schema:\n"
    for table_name, columns in schemas.items():
        prompt_str += f"Table {table_name}:\n"
        for col in columns:
            prompt_str += f"  - {col['name']} ({col['type']})\n"
    return prompt_str

def _call_llm(prompt: str) -> str:
    """
    Calls the configured Generative AI model to generate SQL from a prompt.
    """
    if not llm_model:
        raise RuntimeError("The Generative AI model is not configured. Please set the GEMINI_API_KEY.")

    logger.info("--- Calling real LLM API ---")
    response = llm_model.generate_content(prompt)
    try:
        generated_sql = response.text
        logger.info(f"LLM response received:\n{generated_sql}")
        # Clean up potential markdown formatting from the response
        return re.sub(r"```sql|```", "", generated_sql).strip()
    except Exception as e:
        logger.error(f"Failed to extract text from LLM response: {e}")
        logger.error(f"Full response object: {response}")
        raise

class NlToSqlService:
    def __init__(self, oracle_service: OracleService):
        self._oracle_service = oracle_service
        self._all_known_tables = ["T501_ORDER", "T503_INVOICE", "T504_CONSIGNMENT", "T907_SHIPPING_INFO", "T704_ACCOUNT"]

async def generate_sql_from_text(self, text: str, session_id: Any) -> str:
    """
    Takes natural language text and generates a SQL query using a real LLM.
    """
    relevant_tables = _get_relevant_tables(text, self._all_known_tables)
    if not relevant_tables:
        raise ValueError("Could not identify any relevant tables in your request. Please be more specific (e.g., 'orders', 'invoices').")

    schemas = await self._oracle_service.get_table_schemas(session_id, relevant_tables)
    if not schemas:
        raise ValueError("Could not retrieve schema information for the identified tables.")

    schema_prompt = _format_schema_for_prompt(schemas)
    final_prompt = (
        f"You are an expert Oracle SQL developer. Based on the following schema and user request, "
        f"write a single, valid Oracle SQL SELECT statement. Only output the SQL query and nothing else.\n\n"
        f"{schema_prompt}\n"
        f'User Request: "{text}"'
    )

    generated_sql = await asyncio.to_thread(_call_llm, final_prompt)

    if not generated_sql.lower().strip().startswith('select'):
        raise ValueError("The AI model did not return a valid SELECT query.")
        
    return generated_sql
