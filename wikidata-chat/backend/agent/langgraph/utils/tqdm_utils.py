# backend/agent/langgraph/utils/tqdm_utils.py
from tqdm import tqdm
import logging

# Configure logging
logger = logging.getLogger(__name__)

class DebugTqdm(tqdm):
    """Custom tqdm that reports progress to a debug callback"""
    
    def __init__(self, *args, debug_callback=None, **kwargs):
        self.debug_callback = debug_callback
        self.last_percent = -1
        print(f"DebugTqdm initialized with callback: {debug_callback is not None}")
        logger.info(f"DebugTqdm initialized with callback: {debug_callback is not None}")
        super().__init__(*args, **kwargs)
    
    def display(self, msg=None, pos=None):
        # Call the original display method
        super().display(msg=msg, pos=pos)
        
        # Also send to debug callback if available
        if self.debug_callback and self.total:
            percent = int((self.n / self.total) * 100)
            print(f"Debug tqdm progress: {percent}% ({self.n}/{self.total})")
            
            # Only report when percentage changes to avoid flooding
            if percent > self.last_percent:
                try:
                    self.debug_callback(f"Encoding progress: {percent}% ({self.n}/{self.total})")
                    print(f"Debug callback called successfully for {percent}%")
                except Exception as e:
                    print(f"Error in debug callback: {e}")
                    logger.error(f"Error in debug callback: {e}")
                self.last_percent = percent
