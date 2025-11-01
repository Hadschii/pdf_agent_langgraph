import json
from typing import Dict, Any
from langchain_core.messages import HumanMessage
from langchain_core.prompts import PromptTemplate
from src.state import State
from src.llm_client import get_llm

from src.logger import logger


def text_analysis_node(state: State) -> Dict[str, Any]:
    """Classify, extract entities, and summarize a document using the LLM.

    This function wraps a single LLM call that returns a JSON payload with
    fields `classification`, `entities`, and `summary`. The returned values are
    validated and normalized before being returned as a dict.

    Args:
        state: Workflow state containing `pdf_text`.

    Returns:
        A dict with keys: `classification` (str), `entities` (dict), `summary` (str).
    """
    text = state.get("pdf_text", None)
    if not text:
        raise ValueError("No text found in state for analysis.")

    # Load categories from config
    from src.config_loader import PDFConfig

    config = PDFConfig()
    categories = ", ".join(config.category_list)
    # Prompt template
    prompt = PromptTemplate(
        input_variables=["text", "categories"],
        template="""
        You receive the text of a document. Perform the following tasks:

        1. Classify the document into one of the following categories: {categories}
        2. Extract the organization and document date (if available). For known organizations, use the short official name (e.g. Bayrische Motorenwerke = BMW, IKEA Deutschland GmbH = IKEA, Volkswagen AG = VW).
        3. Provide a brief summary of the content in 1–3 words (without organization, date, or category). If one item, be specific (e.g. iPhone 17 Pro). If you find many items try to summarize (e.g. chair, table, rack -> furniture) 

        Return the response as JSON with the fields:
        - classification (German)
        - entities: {{"Organization": ..., "Document_Date": ...}}
        - summary (German)
        
        ONLY RETURN THE JSON, NO ADDITIONAL TEXT.
        
        Text:
        {text}
        """,
    )

    # Format and send prompt
    message = HumanMessage(content=prompt.format(text=text, categories=categories))
    llm = get_llm()
    response = llm.invoke([message]).content.strip()

    # Parse JSON response
    try:
        parsed = json.loads(response)
        logger.log(f"LLM analysis: {parsed}", level="info")
        return {
            "classification": parsed.get("classification", "").strip(),
            "entities": parsed.get("entities", {}),
            "summary": parsed.get("summary", "").strip(),
        }
    except json.JSONDecodeError as e:
        logger.log(f"Failed to parse LLM response as JSON: {e}\nRaw output:\n{response}", level="error")
        raise ValueError(
            f"Failed to parse LLM response as JSON: {e}\nRaw output:\n{response}"
        )
        

