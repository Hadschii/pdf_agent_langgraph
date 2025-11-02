import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Literal

from dotenv import load_dotenv

# Ensure environment variables are loaded before our components initialize.
load_dotenv()

from langchain_core.runnables.graph import MermaidDrawMethod
from langgraph.graph import START,END, StateGraph

from src.config_loader import PDFConfig
from src.logger import logger
from src.pdf_analyzer import text_analysis_node
from src.pdf_organizer import organization_node
from src.pdf_text_extractor import pdf_extraction_node
from src.img_text_extractor import img_extraction_node
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

    # print(f"Graph written to {output_path}")


def type_detection_node(state: State) -> Literal["pdf_extraction_node", "img_extraction_node"]:
    file = state.get("file_path", "")
    path = Path(file)
    image_exts = {".png", ".jpg", ".jpeg"}
    if path.suffix.lower() in image_exts:
        logger.log(
            f"Image file support is experimental. Extracting text from image file: {file}",
            level="warning",
        )
        return "img_extraction_node"
    return "pdf_extraction_node"


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
    workflow.add_node("pdf_extraction_node", pdf_extraction_node)
    workflow.add_node("img_extraction_node", img_extraction_node)
    workflow.add_node("text_analysis_node", text_analysis_node)
    workflow.add_node("organize_file", organization_node)

    # Add edges to the graph
    workflow.add_conditional_edges(START, type_detection_node)
    workflow.add_edge("pdf_extraction_node", "text_analysis_node")
    workflow.add_edge("img_extraction_node", "text_analysis_node")
    workflow.add_edge("text_analysis_node", "organize_file")
    workflow.add_edge("organize_file", END)

    # Compile the graph
    app = workflow.compile()
    draw_graph(app=app, output_path="pdf_agent_langgraph_graph.png")

    input_path = Path(config.input_folder)
    # Collect all supported file types
    exts = ["*.pdf", "*.png", "*.jpg", "*.jpeg"]
    files = sorted([p for ext in exts for p in input_path.glob(ext)])
    for file_path in files:
        state_input = {"file_path": str(file_path)}
        app.invoke(state_input)
    logger.log(f"Batch processed {len(files)} file(s) in {input_path}")
    
    print("Bye bye from pdf-agent-langgraph! ====================")


if __name__ == "__main__":
    main()
