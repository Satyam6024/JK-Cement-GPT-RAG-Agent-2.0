"""
Improved utility functions for the RAG tools with better error handling and caching.
"""

import logging
import re
from typing import Dict, Optional, Tuple

from google.adk.tools.tool_context import ToolContext
from vertexai import rag

from ..config import LOCATION, PROJECT_ID

logger = logging.getLogger(__name__)

# Cache for corpus information to reduce API calls
_corpus_cache: Dict[str, Dict] = {}
_cache_valid = False


def _refresh_corpus_cache() -> None:
    """Refresh the internal corpus cache."""
    global _corpus_cache, _cache_valid
    try:
        _corpus_cache.clear()
        corpora = rag.list_corpora()
        for corpus in corpora:
            # Cache by both resource name and display name for flexible lookup
            _corpus_cache[corpus.name] = {
                "resource_name": corpus.name,
                "display_name": corpus.display_name,
                "create_time": getattr(corpus, "create_time", ""),
                "update_time": getattr(corpus, "update_time", ""),
            }
            # Also cache by display name if different
            if corpus.display_name != corpus.name:
                _corpus_cache[corpus.display_name] = _corpus_cache[corpus.name]
        
        _cache_valid = True
        logger.info(f"Refreshed corpus cache with {len(set(c['resource_name'] for c in _corpus_cache.values()))} corpora")
    except Exception as e:
        logger.error(f"Failed to refresh corpus cache: {str(e)}")
        _cache_valid = False


def _ensure_cache_valid() -> None:
    """Ensure the corpus cache is valid, refresh if needed."""
    global _cache_valid
    if not _cache_valid:
        _refresh_corpus_cache()


def get_corpus_resource_name(corpus_name: str) -> str:
    """
    Convert a corpus name to its full resource name.
    
    This function handles various input formats:
    1. Full resource names (projects/.../ragCorpora/...)
    2. Display names of existing corpora
    3. Simple names that need to be converted to resource names
    
    Args:
        corpus_name (str): The corpus name, display name, or resource name
        
    Returns:
        str: The full resource name
        
    Raises:
        ValueError: If the corpus name is invalid or empty
    """
    if not corpus_name or not isinstance(corpus_name, str):
        raise ValueError("Corpus name cannot be empty or None")
    
    corpus_name = corpus_name.strip()
    
    # If it's already a full resource name, validate and return
    resource_pattern = r"^projects/[^/]+/locations/[^/]+/ragCorpora/[^/]+$"
    if re.match(resource_pattern, corpus_name):
        logger.info(f"Using provided resource name: {corpus_name}")
        return corpus_name
    
    # Check cache for existing corpus by display name or resource name
    _ensure_cache_valid()
    if corpus_name in _corpus_cache:
        resource_name = _corpus_cache[corpus_name]["resource_name"]
        logger.info(f"Found corpus in cache: {corpus_name} -> {resource_name}")
        return resource_name
    
    # If not found in cache, construct resource name from corpus name
    # Clean the name to be safe for use as a resource ID
    corpus_id = re.sub(r"[^a-zA-Z0-9_-]", "_", corpus_name.lower())
    if not corpus_id:
        raise ValueError(f"Invalid corpus name: '{corpus_name}' produces empty ID")
    
    resource_name = f"projects/{PROJECT_ID}/locations/{LOCATION}/ragCorpora/{corpus_id}"
    logger.info(f"Constructed resource name: {corpus_name} -> {resource_name}")
    return resource_name


def check_corpus_exists(corpus_name: str, tool_context: ToolContext) -> bool:
    """
    Check if a corpus exists, with intelligent caching and state management.
    
    Args:
        corpus_name (str): The corpus name or resource name to check
        tool_context (ToolContext): The tool context for state management
        
    Returns:
        bool: True if the corpus exists, False otherwise
    """
    if not corpus_name:
        # If no corpus name provided, check if there's a current corpus
        current_corpus = get_current_corpus(tool_context)
        if current_corpus:
            corpus_name = current_corpus
        else:
            return False
    
    # Check tool context state first for recent operations
    state_key = f"corpus_exists_{corpus_name}"
    if tool_context.state.get(state_key) is True:
        return True
    elif tool_context.state.get(state_key) is False:
        return False
    
    try:
        # Refresh cache and check
        _ensure_cache_valid()
        
        # Try to find by exact match first
        if corpus_name in _corpus_cache:
            tool_context.state[state_key] = True
            _set_current_corpus_if_empty(corpus_name, tool_context)
            return True
        
        # Try to find by resource name construction
        try:
            resource_name = get_corpus_resource_name(corpus_name)
            if resource_name in _corpus_cache:
                tool_context.state[state_key] = True
                _set_current_corpus_if_empty(corpus_name, tool_context)
                return True
        except ValueError:
            pass  # Invalid corpus name format
        
        # Not found
        tool_context.state[state_key] = False
        return False
        
    except Exception as e:
        logger.error(f"Error checking corpus existence: {str(e)}")
        # Don't cache errors, but assume it doesn't exist for now
        return False


def get_current_corpus(tool_context: ToolContext) -> Optional[str]:
    """
    Get the current corpus from the tool context.
    
    Args:
        tool_context (ToolContext): The tool context
        
    Returns:
        Optional[str]: The current corpus name, or None if not set
    """
    return tool_context.state.get("current_corpus")


def set_current_corpus(corpus_name: str, tool_context: ToolContext) -> bool:
    """
    Set the current corpus in the tool context state.
    
    Args:
        corpus_name (str): The name of the corpus to set as current
        tool_context (ToolContext): The tool context for state management
        
    Returns:
        bool: True if the corpus exists and was set as current, False otherwise
    """
    if check_corpus_exists(corpus_name, tool_context):
        tool_context.state["current_corpus"] = corpus_name
        logger.info(f"Set current corpus to: {corpus_name}")
        return True
    return False


def _set_current_corpus_if_empty(corpus_name: str, tool_context: ToolContext) -> None:
    """
    Set the current corpus only if no current corpus is already set.
    
    Args:
        corpus_name (str): The corpus name to potentially set as current
        tool_context (ToolContext): The tool context
    """
    if not tool_context.state.get("current_corpus"):
        tool_context.state["current_corpus"] = corpus_name
        logger.info(f"Auto-set current corpus to: {corpus_name}")


def resolve_corpus_name(corpus_name: str, tool_context: ToolContext) -> Tuple[str, bool]:
    """
    Resolve a corpus name, using the current corpus if the provided name is empty.
    
    Args:
        corpus_name (str): The provided corpus name (may be empty)
        tool_context (ToolContext): The tool context
        
    Returns:
        Tuple[str, bool]: (resolved_corpus_name, success)
            - resolved_corpus_name: The actual corpus name to use
            - success: True if resolution was successful, False otherwise
    """
    if corpus_name and corpus_name.strip():
        return corpus_name.strip(), True
    
    # Try to use current corpus
    current_corpus = get_current_corpus(tool_context)
    if current_corpus:
        logger.info(f"Using current corpus: {current_corpus}")
        return current_corpus, True
    
    logger.warning("No corpus name provided and no current corpus set")
    return "", False


def invalidate_corpus_cache() -> None:
    """
    Invalidate the corpus cache to force a refresh on next access.
    Call this after creating or deleting corpora.
    """
    global _cache_valid
    _cache_valid = False
    logger.info("Invalidated corpus cache")


def get_corpus_display_info(corpus_name: str) -> Dict[str, str]:
    """
    Get display information for a corpus.
    
    Args:
        corpus_name (str): The corpus name or resource name
        
    Returns:
        Dict[str, str]: Display information including display_name and resource_name
    """
    _ensure_cache_valid()
    
    if corpus_name in _corpus_cache:
        return {
            "display_name": _corpus_cache[corpus_name]["display_name"],
            "resource_name": _corpus_cache[corpus_name]["resource_name"],
        }
    
    # If not in cache, try to construct and return basic info
    try:
        resource_name = get_corpus_resource_name(corpus_name)
        return {
            "display_name": corpus_name,
            "resource_name": resource_name,
        }
    except ValueError:
        return {
            "display_name": corpus_name,
            "resource_name": corpus_name,
        }