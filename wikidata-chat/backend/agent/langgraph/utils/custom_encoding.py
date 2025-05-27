# backend/agent/langgraph/utils/custom_encoding.py
import logging
from typing import List, Dict, Any, Optional, Callable
import numpy as np

logger = logging.getLogger(__name__)

def encode_with_progress(
    model, 
    sentences: List[str], 
    batch_size: int = 32, 
    show_progress_bar: bool = False, 
    debug_callback: Optional[Callable] = None,
    **kwargs
) -> np.ndarray:
    """
    Custom wrapper around SentenceTransformer.encode to report progress via debug_callback
    
    Args:
        model: The SentenceTransformer model
        sentences: List of sentences to encode
        batch_size: Batch size for encoding
        show_progress_bar: Whether to show progress bar
        debug_callback: Function to call with progress updates
        **kwargs: Additional arguments to pass to encode
        
    Returns:
        Numpy array of embeddings
    """
    # Calculate total batches for reporting
    total_items = len(sentences)
    total_batches = (total_items + batch_size - 1) // batch_size
    
    if debug_callback:
        debug_callback(f"Starting encoding of {total_items} items in {total_batches} batches")
    
    # Process in batches with progress reporting
    all_embeddings = []
    for i in range(0, total_items, batch_size):
        batch = sentences[i:i+batch_size]
        batch_num = i // batch_size + 1
        
        if debug_callback:
            percent = int((batch_num / total_batches) * 100)
            debug_callback(f"Encoding progress: {percent}% (batch {batch_num}/{total_batches})")
            
        # Encode batch
        batch_embeddings = model.encode(
            batch, 
            batch_size=batch_size, 
            show_progress_bar=False,  # Disable internal progress bar
            **kwargs
        )
        
        all_embeddings.append(batch_embeddings)
    
    # Combine all batches
    combined_embeddings = np.vstack(all_embeddings) if all_embeddings else np.array([])
    
    if debug_callback:
        debug_callback(f"Encoding complete: {total_items} items processed")
        
    return combined_embeddings
