"""
Improved RAG query tool with better error handling and response processing.
"""

import logging
from typing import Dict, List, Any

from google.adk.tools.tool_context import ToolContext
from vertexai import rag

from ..config import DEFAULT_DISTANCE_THRESHOLD, DEFAULT_TOP_K
from .utils import (
    check_corpus_exists,
    get_corpus_resource_name,
    resolve_corpus_name,
    set_current_corpus,
    get_corpus_display_info,
)

logger = logging.getLogger(__name__)


def rag_query(
    corpus_name: str,
    query: str,
    tool_context: ToolContext,
) -> Dict[str, Any]:
    """
    Query a Vertex AI RAG corpus with improved error handling and response processing.

    Args:
        corpus_name (str): The name of the corpus to query. If empty, uses current corpus.
        query (str): The text query to search for in the corpus
        tool_context (ToolContext): The tool context

    Returns:
        Dict[str, Any]: The query results and status with enhanced information
    """
    # Input validation
    if not query or not isinstance(query, str) or not query.strip():
        return {
            "status": "error",
            "message": "Query cannot be empty. Please provide a question or search term.",
            "query": query,
            "corpus_name": corpus_name,
        }

    query = query.strip()

    # Resolve corpus name
    resolved_corpus, success = resolve_corpus_name(corpus_name, tool_context)
    if not success:
        return {
            "status": "error",
            "message": (
                "No corpus specified and no current corpus available. "
                "Please specify a corpus name or create a corpus first."
            ),
            "query": query,
            "corpus_name": corpus_name,
            "suggestion": "Try using the list_corpora tool to see available corpora",
        }

    corpus_name = resolved_corpus

    # Check if the corpus exists
    if not check_corpus_exists(corpus_name, tool_context):
        return {
            "status": "error",
            "message": f"Corpus '{corpus_name}' does not exist.",
            "query": query,
            "corpus_name": corpus_name,
            "suggestion": "Use list_corpora to see available corpora or create_corpus to create a new one",
        }

    try:
        # Get corpus display information
        corpus_info = get_corpus_display_info(corpus_name)
        display_name = corpus_info["display_name"]
        
        # Get the corpus resource name
        corpus_resource_name = get_corpus_resource_name(corpus_name)
        
        logger.info(f"Querying corpus '{display_name}' with query: '{query[:100]}...'")

        # Configure retrieval parameters
        rag_retrieval_config = rag.RagRetrievalConfig(
            top_k=DEFAULT_TOP_K,
            filter=rag.Filter(vector_distance_threshold=DEFAULT_DISTANCE_THRESHOLD),
        )

        # Perform the query
        response = rag.retrieval_query(
            rag_resources=[
                rag.RagResource(
                    rag_corpus=corpus_resource_name,
                )
            ],
            text=query,
            rag_retrieval_config=rag_retrieval_config,
        )

        # Process the response into a structured format
        results = _process_retrieval_response(response)

        # Set this corpus as current since we successfully used it
        set_current_corpus(corpus_name, tool_context)

        # Return appropriate response based on results
        if not results:
            return {
                "status": "warning",
                "message": f"No relevant results found in corpus '{display_name}' for your query.",
                "query": query,
                "corpus_name": corpus_name,
                "corpus_display_name": display_name,
                "results": [],
                "results_count": 0,
                "suggestions": [
                    "Try rephrasing your question",
                    "Use more general search terms",
                    "Check if the relevant documents are in the corpus using get_corpus_info",
                ],
            }

        # Filter results by relevance score
        high_relevance = [r for r in results if r.get("score", 0) > 0.7]
        medium_relevance = [r for r in results if 0.4 <= r.get("score", 0) <= 0.7]
        
        return {
            "status": "success",
            "message": f"Found {len(results)} relevant result(s) in corpus '{display_name}'",
            "query": query,
            "corpus_name": corpus_name,
            "corpus_display_name": display_name,
            "results": results,
            "results_count": len(results),
            "high_relevance_count": len(high_relevance),
            "medium_relevance_count": len(medium_relevance),
            "search_config": {
                "top_k": DEFAULT_TOP_K,
                "distance_threshold": DEFAULT_DISTANCE_THRESHOLD,
            },
        }

    except Exception as e:
        error_msg = f"Error querying corpus '{corpus_name}': {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        # Provide more specific error messages based on common issues
        if "not found" in str(e).lower():
            suggestion = "The corpus may have been deleted. Try listing available corpora."
        elif "permission" in str(e).lower():
            suggestion = "Check if you have permission to access this corpus."
        elif "quota" in str(e).lower():
            suggestion = "You may have hit API quota limits. Try again in a few minutes."
        else:
            suggestion = "Check your Vertex AI configuration and network connection."

        return {
            "status": "error",
            "message": error_msg,
            "query": query,
            "corpus_name": corpus_name,
            "suggestion": suggestion,
            "error_type": type(e).__name__,
        }


def _process_retrieval_response(response) -> List[Dict[str, Any]]:
    """
    Process the RAG retrieval response into a structured format.
    
    Args:
        response: The response from rag.retrieval_query()
        
    Returns:
        List[Dict[str, Any]]: Processed results with enhanced metadata
    """
    results = []
    
    if not hasattr(response, "contexts") or not response.contexts:
        return results
    
    for i, ctx_group in enumerate(response.contexts.contexts):
        try:
            # Extract basic information
            result = {
                "rank": i + 1,
                "text": getattr(ctx_group, "text", ""),
                "score": getattr(ctx_group, "score", 0.0),
                "source_uri": getattr(ctx_group, "source_uri", ""),
                "source_name": getattr(ctx_group, "source_display_name", ""),
            }
            
            # Enhance with additional metadata
            result["text_length"] = len(result["text"])
            result["relevance_level"] = _categorize_relevance(result["score"])
            
            # Clean up source information
            if result["source_uri"]:
                result["source_type"] = _identify_source_type(result["source_uri"])
            
            # Only add if we have meaningful content
            if result["text"].strip():
                results.append(result)
                
        except Exception as e:
            logger.warning(f"Error processing retrieval result {i}: {str(e)}")
            continue
    
    # Sort by relevance score (descending)
    results.sort(key=lambda x: x.get("score", 0), reverse=True)
    
    return results


def _categorize_relevance(score: float) -> str:
    """
    Categorize relevance based on similarity score.
    
    Args:
        score (float): The similarity score
        
    Returns:
        str: Relevance category
    """
    if score >= 0.8:
        return "very_high"
    elif score >= 0.7:
        return "high"
    elif score >= 0.5:
        return "medium"
    elif score >= 0.3:
        return "low"
    else:
        return "very_low"


def _identify_source_type(source_uri: str) -> str:
    """
    Identify the type of source based on the URI.
    
    Args:
        source_uri (str): The source URI
        
    Returns:
        str: The source type
    """
    if "drive.google.com" in source_uri:
        return "google_drive"
    elif "docs.google.com" in source_uri:
        if "/document/" in source_uri:
            return "google_docs"
        elif "/spreadsheets/" in source_uri:
            return "google_sheets"
        elif "/presentation/" in source_uri:
            return "google_slides"
        else:
            return "google_workspace"
    elif source_uri.startswith("gs://"):
        return "google_cloud_storage"
    elif source_uri.startswith("http"):
        return "web_url"
    else:
        return "unknown"