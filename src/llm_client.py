from dotenv import load_dotenv
from typing import Optional

# Do NOT create the LLM at import time; provide a lazy factory instead.
load_dotenv()

from src.config_loader import PDFConfig
from langchain_openai import ChatOpenAI

_llm: Optional[ChatOpenAI] = None


def get_llm() -> ChatOpenAI:
	"""Return a shared ChatOpenAI instance, creating it on first use.

	This avoids heavy side-effects at import time and makes importing
	modules safe during test/analysis runs.
	"""
	global _llm
	if _llm is None:
		config = PDFConfig()
		_llm = ChatOpenAI(model=config.llm_model, temperature=config.llm_temperature)
	return _llm


__all__ = ["get_llm"]
