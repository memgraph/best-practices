"""
Ingestion endpoints for processing documents into the knowledge graph.
"""
import os
import json
import logging
import sys
from fastapi import APIRouter, HTTPException, Request

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unstructured2graph import from_unstructured, make_chunks, compute_embeddings
from resources import initialize_resources

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingestion"])


@router.post("")
async def ingest_documents(request: Request):
    """
    Ingest unstructured documents from URLs into Memgraph using unstructured2graph.
    
    Expected JSON body:
    {
        "urls": ["url1", "url2", ...],
        "only_chunks": false,
        "link_chunks": true,
        "create_vector_index": true,
        "cleanup": true
    }
    """
    # Parse request body
    try:
        body = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON in request body"
        )
    
    # Extract parameters with defaults
    urls = body.get("urls", [])
    only_chunks = body.get("only_chunks", False)
    link_chunks = body.get("link_chunks", True)
    create_vector_index = body.get("create_vector_index", True)
    cleanup = body.get("cleanup", True)
    
    # Verify OPENAI_API_KEY is set
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY environment variable is not set. Please set your OpenAI API key."
        )

    if not urls or not isinstance(urls, list):
        raise HTTPException(
            status_code=400,
            detail="No URLs provided. Please provide at least one URL in the 'urls' array."
        )

    try:
        logger.info(f"Processing {len(urls)} documentation pages. Starting ingestion...")

        memgraph, lightrag_wrapper = await initialize_resources(cleanup=cleanup, create_vector_index=create_vector_index)

        # Ingest documents
        await from_unstructured(
            urls,
            memgraph,
            lightrag_wrapper,
            only_chunks=only_chunks,
            link_chunks=link_chunks,
        )

        # Create vector index and compute embeddings if requested
        if create_vector_index:
            logger.info("Creating vector search index and computing embeddings...")
            try:
                compute_embeddings(memgraph, "Chunk")
                logger.info("Successfully created vector index and computed embeddings")
            except Exception as e:
                logger.warning(f"Error creating vector index or computing embeddings: {str(e)}")

        logger.info("Successfully ingested all documentation pages into Memgraph!")

        return {
            "message": "Successfully ingested all documentation pages into Memgraph!",
            "urls_processed": len(urls),
            "status": "completed"
        }

    except Exception as e:
        logger.error(f"Error during ingestion: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error during ingestion: {str(e)}"
        )


@router.post("/single")
async def ingest_single_document(request: Request):
    """
    Ingest a single document from a URL into Memgraph.
    Useful for progress tracking - process one document at a time.
    
    Expected JSON body:
    {
        "url": "https://example.com/doc",
        "only_chunks": false,
        "link_chunks": true,
        "create_vector_index": true,
        "cleanup": false  # Usually false for single document ingestion
    }
    """
    # Parse request body
    try:
        body = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON in request body"
        )
    
    # Extract parameters with defaults
    url = body.get("url")
    only_chunks = body.get("only_chunks", False)
    link_chunks = body.get("link_chunks", True)
    create_vector_index = body.get("create_vector_index", True)
    cleanup = body.get("cleanup", False)
    
    # Verify OPENAI_API_KEY is set
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY environment variable is not set. Please set your OpenAI API key."
        )

    if not url or not isinstance(url, str):
        raise HTTPException(
            status_code=400,
            detail="No URL provided. Please provide a 'url' string."
        )

    try:
        logger.info(f"Processing single document: {url}")

        memgraph, lightrag_wrapper = await initialize_resources(cleanup=cleanup, create_vector_index=create_vector_index)

        # Ingest single document
        await from_unstructured(
            [url],
            memgraph,
            lightrag_wrapper,
            only_chunks=only_chunks,
            link_chunks=link_chunks,
        )

        # Create vector index and compute embeddings if requested
        if create_vector_index:
            logger.info("Computing embeddings and creating vector search index...")
            try:
                # Compute embeddings for all chunks (including newly added ones)
                compute_embeddings(memgraph, "Chunk")
                logger.info("Successfully computed embeddings and created vector index")
            except Exception as e:
                logger.warning(f"Error computing embeddings or creating vector index: {str(e)}")

        logger.info(f"Successfully ingested document: {url}")

        return {
            "message": f"Successfully ingested document: {url}",
            "url": url,
            "status": "completed"
        }

    except Exception as e:
        logger.error(f"Error during ingestion: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error during ingestion: {str(e)}"
        )


@router.post("/estimate")
async def estimate_ingestion(request: Request):
    """
    Estimate the number of chunks and processing time for given URLs.
    Returns chunk count per document and total estimated time (10 seconds per chunk).
    
    Expected JSON body:
    {
        "urls": ["url1", "url2", ...]
    }
    """
    try:
        body = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON in request body"
        )
    
    urls = body.get("urls", [])
    
    if not urls or not isinstance(urls, list):
        raise HTTPException(
            status_code=400,
            detail="No URLs provided. Please provide at least one URL in the 'urls' array."
        )
    
    try:
        # Get chunk estimates without full processing
        chunked_documents = make_chunks(urls)
        
        estimates = []
        total_chunks = 0
        
        for doc in chunked_documents:
            chunk_count = len(doc.chunks)
            total_chunks += chunk_count
            estimated_time = chunk_count * 10  # 10 seconds per chunk
            
            estimates.append({
                "url": str(doc.source),
                "chunk_count": chunk_count,
                "estimated_time_seconds": estimated_time
            })
        
        total_estimated_time = total_chunks * 10
        
        return {
            "total_chunks": total_chunks,
            "total_estimated_time_seconds": total_estimated_time,
            "documents": estimates
        }
    
    except Exception as e:
        logger.error(f"Error estimating ingestion: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error estimating ingestion: {str(e)}"
        )

