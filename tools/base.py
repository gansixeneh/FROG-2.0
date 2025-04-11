# tools/base.py
from langchain.tools import BaseTool
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class WikidataBaseTool(BaseTool):
    """Base class for all Wikidata QA tools with common utilities."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = logging.getLogger(self.__class__.__name__)

    def _log_input_output(self, input_data: Any, output: Any) -> None:
        """Log tool input and output for debugging."""
        self.logger.debug(f"Input: {input_data}")
        self.logger.debug(f"Output: {output}")