import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv

# Ensure environment variables are loaded before our components initialize.
load_dotenv()

from langchain_core.runnables.graph import MermaidDrawMethod
from langgraph.graph import END, StateGraph

from src.config_loader import PDFConfig
from src.logger import logger
from src.pdf_analyzer import text_analysis_node
from src.pdf_organizer import organization_node
from src.pdf_text_extractor import text_extraction_node
from src.state import State

config = PDFConfig()


def draw_graph(app: Any, output_path: str = "graph.png") -> None:
    """Write the compiled graph PNG to disk.

    Args:
        app: Compiled workflow application object returned by StateGraph.compile().
        output_path: Path where the PNG should be written.

    Usage: call after `app = workflow.compile()` with the compiled `app`.
    """
    png = app.get_graph().draw_mermaid_png(draw_method=MermaidDrawMethod.API)

    # bytes -> write directly
    if isinstance(png, (bytes, bytearray)):
        open(output_path, "wb").write(png)
    # base64 or plain string -> try decode, otherwise write bytes
    elif isinstance(png, str):
        import base64

        try:
            data = base64.b64decode(png)
        except Exception:
            data = png.encode()
        open(output_path, "wb").write(data)
    else:
        # try PIL save or fallback to bytes()
        try:
            png.save(output_path, format="PNG")
        except Exception:
            open(output_path, "wb").write(bytes(png))

    print(f"Graph written to {output_path}")


def main() -> None:
    """Entry point: build the workflow and process PDFs found in the input folder.

    The function builds the StateGraph, compiles it into an app and invokes the
    app for each PDF file located in the configured input folder.
    """
    print("Hello from pdf-agent-langgraph! ====================")

    logger.log(
        f"STARTING PDF PROCESSING ON {datetime.now().strftime('%Y-%m-%d at %H:%M:%S')}",
        level="info",
    )
    logger.log(f"from path {config.input_folder}", level="info")

    # Create our StateGraph
    workflow = StateGraph(State)

    # Add nodes to the graph
    workflow.add_node("pdf_text_extraction", text_extraction_node)
    workflow.add_node("text_analysis_node", text_analysis_node)
    workflow.add_node("organize_file", organization_node)

    # Add edges to the graph
    workflow.set_entry_point("pdf_text_extraction")  # Set the entry point of the graph
    workflow.add_edge("pdf_text_extraction", "text_analysis_node")
    workflow.add_edge("text_analysis_node", "organize_file")
    workflow.add_edge("organize_file", END)

    # Compile the graph
    app = workflow.compile()
    # draw_graph(app=app, output_path="pdf_agent_langgraph_graph.png")

    # Use pathlib for more robust path handling
    input_path = Path(config.input_folder)
    pdfs = list(input_path.glob("*.pdf"))
    for pdf_path in pdfs:
        state_input = {"pdf_path": str(pdf_path)}
        app.invoke(state_input)
    logger.log(f"Batch processed {len(pdfs)} PDF(s) in {input_path}")

    print("Bye bye from pdf-agent-langgraph! ====================")


if __name__ == "__main__":
    main()
