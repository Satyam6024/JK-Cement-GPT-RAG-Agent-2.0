"""
Vertex AI RAG Agent Package

A comprehensive package for interacting with Google Cloud Vertex AI RAG capabilities.
This package provides tools for creating, managing, and querying RAG corpora.
"""

import os
import logging
from typing import Optional

import vertexai
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get Vertex AI configuration from environment
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION")

# Track initialization status
_vertex_ai_initialized = False
_initialization_error: Optional[str] = None


def initialize_vertex_ai() -> bool:
    """
    Initialize Vertex AI with proper error handling.
    
    Returns:
        bool: True if initialization was successful, False otherwise
    """
    global _vertex_ai_initialized, _initialization_error
    
    if _vertex_ai_initialized:
        return True
    
    try:
        if not PROJECT_ID or not LOCATION:
            missing = []
            if not PROJECT_ID:
                missing.append("GOOGLE_CLOUD_PROJECT")
            if not LOCATION:
                missing.append("GOOGLE_CLOUD_LOCATION")
            
            error_msg = f"Missing required environment variables: {', '.join(missing)}"
            logger.error(error_msg)
            _initialization_error = error_msg
            return False
        
        logger.info(f"Initializing Vertex AI with project={PROJECT_ID}, location={LOCATION}")
        vertexai.init(project=PROJECT_ID, location=LOCATION)
        
        _vertex_ai_initialized = True
        logger.info("Vertex AI initialization successful")
        return True
        
    except Exception as e:
        error_msg = f"Failed to initialize Vertex AI: {str(e)}"
        logger.error(error_msg)
        _initialization_error = error_msg
        return False


def get_initialization_status() -> tuple[bool, Optional[str]]:
    """
    Get the current initialization status.
    
    Returns:
        tuple: (is_initialized, error_message)
    """
    return _vertex_ai_initialized, _initialization_error


def require_vertex_ai():
    """
    Ensure Vertex AI is initialized, raise exception if not.
    
    Raises:
        RuntimeError: If Vertex AI is not properly initialized
    """
    if not _vertex_ai_initialized:
        initialize_vertex_ai()
        if not _vertex_ai_initialized:
            raise RuntimeError(f"Vertex AI not initialized: {_initialization_error}")


# Initialize Vertex AI when the package is imported
initialize_vertex_ai()

# Package version
__version__ = "1.0.0"

# Export key components (but don't import agent to avoid circular imports)
__all__ = [
    "PROJECT_ID",
    "LOCATION", 
    "initialize_vertex_ai",
    "get_initialization_status",
    "require_vertex_ai",
]