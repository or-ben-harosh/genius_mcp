"""
Annotation tool for batch processing of Genius annotation explanations
"""

import json
import logging
import time
from typing import List
from api.genius_api import GeniusAPI
from utils.utils import safe_json_response
from core.cache_manager import get_cache_key, get_cached, set_cache
from core.rate_limiter import check_rate_limit, get_rate_limit_info
from core.config import GENIUS_API_TOKEN, MAX_REQUESTS_PER_MINUTE, MAX_ANNOTATION_IDS

logger = logging.getLogger(__name__)


async def get_annotation(annotation_ids: List[int]) -> str:
    """
    Get annotation explanations by IDs (batch processing).

    Enhanced with validation, caching, and rate limiting for multiple annotations.

    Args:
        annotation_ids: List of annotation IDs (e.g., [2310153, 1234567])
                       Maximum of 50 IDs per request (configurable)

    Returns:
        JSON: List of annotation results with {"annotation_id", "lyric", "explanation", "success"} for each
    """
    # Rate limiting check
    if not check_rate_limit():
        return safe_json_response({
            "error": "Rate limit exceeded",
            "message": f"Maximum {MAX_REQUESTS_PER_MINUTE} requests per minute allowed",
            "type": "rate_limit_error",
            "rate_limit_info": get_rate_limit_info()
        })

    start_time = time.time()

    try:
        # Input validation
        if not annotation_ids or not isinstance(annotation_ids, list):
            logger.error(f"Invalid annotation_ids input: {annotation_ids}")
            raise ValueError("annotation_ids must be a non-empty list of integers")

        if len(annotation_ids) > MAX_ANNOTATION_IDS:
            logger.error(f"Too many annotation IDs. Maximum allowed: {MAX_ANNOTATION_IDS}, received: {len(annotation_ids)}")
            raise ValueError(f"Too many annotation IDs. Maximum allowed: {MAX_ANNOTATION_IDS}, received: {len(annotation_ids)}")

        # Validate each ID is numeric
        for i, ann_id in enumerate(annotation_ids):
            if not isinstance(ann_id, int) or ann_id <= 0:
                logger.error(f"Invalid annotation ID at index {i}: {ann_id}. All IDs must be positive integers.")
                raise ValueError(f"Invalid annotation ID at index {i}: {ann_id}. All IDs must be positive integers.")

        logger.info(f"Fetching {len(annotation_ids)} annotations: {annotation_ids}")

        results = []
        api = GeniusAPI(GENIUS_API_TOKEN)

        for ann_id in annotation_ids:
            ann_id_str = str(ann_id)

            # Check cache first
            cache_key = get_cache_key("annotation", ann_id_str)
            cached_result = get_cached(cache_key)

            if cached_result:
                logger.info(f"Cache hit for annotation {ann_id}")
                # Parse cached JSON and add to results
                try:
                    cached_data = json.loads(cached_result)
                    results.append(cached_data)
                    continue
                except json.JSONDecodeError:
                    # If cached data is malformed, fetch fresh
                    logger.warning(f"Malformed cached data for annotation {ann_id}, fetching fresh")
                    pass

            # Fetch from API
            try:
                result = await api.get_annotation_explanation(ann_id_str)

                # Cache the result
                set_cache(cache_key, result)

                # Parse and add to results
                result_data = json.loads(result)
                results.append(result_data)

                logger.info(f"Successfully fetched annotation {ann_id}")

            except (ConnectionError, RuntimeError, ValueError, PermissionError, TimeoutError) as e:
                # Add error result for this specific annotation
                error_result = {
                    "annotation_id": ann_id_str,
                    "lyric": "",
                    "explanation": f"Error fetching annotation: {str(e)}",
                    "success": False,
                    "error": str(e),
                    "url": f"https://genius.com/annotations/{ann_id_str}"
                }
                results.append(error_result)
                logger.error(f"Error fetching annotation {ann_id}: {e}")

        elapsed = time.time() - start_time
        successful_count = sum(1 for r in results if r.get("success", False))
        logger.info(f"Batch annotation fetch completed in {elapsed:.2f}s. Success: {successful_count}/{len(annotation_ids)}")

        # Return batch results
        return safe_json_response({
            "annotations": results,
            "total_requested": len(annotation_ids),
            "successful": successful_count,
            "failed": len(annotation_ids) - successful_count,
            "processing_time": elapsed
        })

    except ValueError as e:
        logger.warning(f"Validation error for annotation batch: {e}")
        return safe_json_response({
            "error": "Invalid input",
            "message": str(e),
            "type": "validation_error",
            "annotation_ids": annotation_ids if isinstance(annotation_ids, list) else []
        })

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"Unexpected error in batch annotation fetch after {elapsed:.2f}s: {e}", exc_info=True)
        return safe_json_response({
            "error": "Unexpected error",
            "message": "An unexpected error occurred while fetching annotations",
            "type": "internal_error",
            "details": str(e),
            "annotation_ids": annotation_ids if isinstance(annotation_ids, list) else []
        })
