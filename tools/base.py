# tools/base.py
from langchain.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr
from typing import Any, Dict, List, Optional, ClassVar, Union, Type
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class WikidataBaseTool(BaseTool):
    """Base class for all Wikidata QA tools with common utilities."""
    
    # Use ClassVar for class-level fields that are inherited
    name: ClassVar[str]
    description: ClassVar[str]
    
    # Use PrivateAttr for attributes that shouldn't be validated by Pydantic
    _logger = PrivateAttr()
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._logger = logging.getLogger(self.__class__.__name__)

    def _log_input_output(self, input_data: Any, output: Any) -> None:
        """Log tool input and output for debugging."""
        self._logger.debug(f"Input: {input_data}")
        self._logger.debug(f"Output: {output}")