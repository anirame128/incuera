"""Molmo 2 video analysis service using OpenRouter API."""
import json
import re
from typing import Dict, Any, List
import httpx

from app.config import settings
from app.utils.logger import logger


class MolmoAnalyzer:
    """Service for analyzing session replay videos using Molmo 2 via OpenRouter API."""

    def __init__(self):
        """Initialize OpenRouter API-based analyzer."""
        self.api_key = settings.molmo_api_key
        self.model = settings.molmo_api_model
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        
        if not self.api_key:
            raise ValueError("API key required. Set MOLMO_API_KEY environment variable.")
        
        # Log API key info (masked for security)
        api_key_preview = f"{self.api_key[:10]}..." if self.api_key and len(self.api_key) > 10 else "None"
        logger.info(f"[MOLMO] Initialized with model: {self.model}, API key: {api_key_preview}")
        
        # Check balance on initialization (optional, can be disabled if too slow)
        try:
            self._check_balance()
        except Exception as e:
            logger.warning(f"[MOLMO] Could not check balance (non-fatal): {e}")

    def _check_balance(self) -> Dict[str, float]:
        """Check OpenRouter account balance."""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
            }
            with httpx.Client(timeout=10.0) as client:
                response = client.get("https://openrouter.ai/api/v1/credits", headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    credits_data = data.get("data", {})
                    total = credits_data.get("total_credits", 0)
                    used = credits_data.get("total_usage", 0)
                    remaining = total - used
                    logger.info(f"[MOLMO] Account balance - Total: ${total:.2f}, Used: ${used:.2f}, Remaining: ${remaining:.2f}")
                    return {"total": total, "used": used, "remaining": remaining}
                else:
                    logger.warning(f"[MOLMO] Could not check balance: {response.status_code} - {response.text}")
                    return {}
        except Exception as e:
            logger.warning(f"[MOLMO] Balance check failed: {e}")
            return {}

    def _run_inference(self, video_url: str, prompt: str, max_tokens: int = 2048) -> str:
        """
        Run inference via OpenRouter API.

        Args:
            video_url: URL to the video file (must be publicly accessible)
            prompt: Text prompt for the model
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text response
        """
        logger.info(f"[MOLMO] Running inference via OpenRouter with model {self.model}")
        logger.info(f"[MOLMO] API key present: {bool(self.api_key)}, key prefix: {self.api_key[:10] if self.api_key else 'None'}...")

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "video_url",
                        "video_url": {"url": video_url}
                    }
                ]
            }
        ]
        
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://incuera.com",  # Identify your app
            "X-Title": "Incuera Video Analysis",  # Identify your app
        }

        logger.info(f"[MOLMO] Sending request to {self.base_url} with model {self.model}")
        logger.debug(f"[MOLMO] Request payload: {json.dumps(payload, indent=2)}")

        try:
            with httpx.Client(timeout=300.0) as client:  # 5 minute timeout
                response = client.post(self.base_url, json=payload, headers=headers)
                logger.info(f"[MOLMO] Response status: {response.status_code}")
                
                # Log response for debugging
                if response.status_code != 200:
                    logger.error(f"[MOLMO] Error response: {response.text}")
                
                response.raise_for_status()
                
                result = response.json()
                
                # Extract text from response
                if "choices" in result and len(result["choices"]) > 0:
                    return result["choices"][0]["message"]["content"]
                else:
                    raise ValueError(f"Unexpected response format: {result}")
                        
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text if e.response else str(e)
            status_code = e.response.status_code if e.response else 0
            
            # Parse error message if it's JSON
            error_message = error_detail
            try:
                if e.response:
                    error_json = e.response.json()
                    if "error" in error_json:
                        error_message = error_json["error"].get("message", error_detail)
            except (json.JSONDecodeError, KeyError):
                pass
            
            logger.error(f"[MOLMO] HTTP error: {status_code} - {error_message}")
            
            # Provide user-friendly error messages
            if status_code == 402:
                # Check balance to provide more helpful error message
                balance_info = self._check_balance()
                balance_msg = ""
                if balance_info:
                    remaining = balance_info.get("remaining", 0)
                    balance_msg = f" Your current balance is ${remaining:.2f}."
                
                raise Exception(
                    f"OpenRouter requires payment for video processing. "
                    f"Error: {error_message}.{balance_msg} "
                    f"Please ensure you have at least $1.00 in your OpenRouter account. "
                    f"Check your balance at https://openrouter.ai/credits"
                )
            elif status_code == 401:
                raise Exception(
                    f"OpenRouter API authentication failed. "
                    f"Please check your MOLMO_API_KEY environment variable."
                )
            else:
                raise Exception(f"API request failed ({status_code}): {error_message}")
        except Exception as e:
            logger.error(f"[MOLMO] Inference failed: {e}", exc_info=True)
            # Re-raise if it's already a formatted exception
            if "OpenRouter requires" in str(e) or "authentication failed" in str(e):
                raise
            raise Exception(f"API inference failed: {str(e)}") from e

    def _parse_json_from_text(self, text: str) -> Any:
        """Extract JSON from model response text."""
        # Try to find JSON in the response
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        # Try array format
        array_match = re.search(r'\[.*\]', text, re.DOTALL)
        if array_match:
            try:
                return json.loads(array_match.group())
            except json.JSONDecodeError:
                pass
        
        # If no JSON found, return the text as-is
        logger.warning(f"[MOLMO] Could not parse JSON from response: {text[:200]}")
        return text

    def _dense_caption(self, video_url: str) -> str:
        """Generate dense caption/summary of the session."""
        prompt = (
            "Describe in detail what happens in this web session replay video. "
            "Include all user interactions (clicks, scrolls, form inputs), page navigations, and key events. "
            "Provide a chronological narrative of the user's journey through the website."
        )
        try:
            result = self._run_inference(video_url, prompt)
            logger.info("[MOLMO] Dense caption generated")
            return result
        except Exception as e:
            logger.error(f"[MOLMO] Dense caption failed: {e}", exc_info=True)
            return f"[Analysis error: {str(e)}]"

    def _detect_interactions(self, video_url: str) -> Dict[str, Any]:
        """Detect user interactions (clicks, hovers, scrolls)."""
        prompt = (
            "Identify all user interactions in this video: mouse clicks, hovers, scrolls, and form field interactions. "
            "For each interaction, provide: (1) timestamp in milliseconds, (2) screen coordinates (x, y), "
            "(3) type of interaction, (4) UI element if identifiable. "
            "Format as JSON array with keys: timestamp_ms, x, y, type, element."
        )
        try:
            result = self._run_inference(video_url, prompt)
            parsed = self._parse_json_from_text(result)
            logger.info("[MOLMO] Interactions detected")
            return parsed if isinstance(parsed, dict) else {"clicks": [], "hovers": [], "scrolls": []}
        except Exception as e:
            logger.error(f"[MOLMO] Interaction detection failed: {e}", exc_info=True)
            return {"clicks": [], "hovers": [], "scrolls": [], "error": str(e)}

    def _count_actions(self, video_url: str) -> Dict[str, int]:
        """Count different types of actions."""
        prompt = (
            "Count the following actions in this video: total clicks, total scrolls, form field interactions, "
            "page navigations, button presses. For each action type, provide the count. "
            "Format as JSON object with keys: clicks, scrolls, form_interactions, navigations, button_presses."
        )
        try:
            result = self._run_inference(video_url, prompt)
            parsed = self._parse_json_from_text(result)
            logger.info("[MOLMO] Actions counted")
            return parsed if isinstance(parsed, dict) else {}
        except Exception as e:
            logger.error(f"[MOLMO] Action counting failed: {e}", exc_info=True)
            return {"error": str(e)}

    def _detect_errors(self, video_url: str) -> List[Dict[str, Any]]:
        """Detect errors and anomalies."""
        prompt = (
            "Identify any errors, anomalies, or issues in this web session replay video. "
            "For each error, provide: (1) timestamp in milliseconds, (2) type of error, "
            "(3) description. Format as JSON array with keys: timestamp_ms, type, description."
        )
        try:
            result = self._run_inference(video_url, prompt)
            parsed = self._parse_json_from_text(result)
            logger.info("[MOLMO] Errors detected")
            return parsed if isinstance(parsed, list) else []
        except Exception as e:
            logger.error(f"[MOLMO] Error detection failed: {e}", exc_info=True)
            return [{"type": "analysis_error", "description": str(e), "timestamp_ms": 0}]

    def _track_funnel(self, video_url: str) -> Dict[str, Any]:
        """Track conversion funnel progression."""
        prompt = (
            "Analyze this web session replay video to identify conversion funnel steps. "
            "Identify key steps like: landing, product view, add to cart, checkout start, checkout complete. "
            "For each step, provide: (1) step name, (2) timestamp in milliseconds, (3) whether it was completed. "
            "Format as JSON object with keys: steps (array of {name, timestamp_ms, completed}), "
            "completed (boolean), drop_off_step (string or null)."
        )
        try:
            result = self._run_inference(video_url, prompt)
            parsed = self._parse_json_from_text(result)
            logger.info("[MOLMO] Funnel tracked")
            return parsed if isinstance(parsed, dict) else {"steps": [], "completed": False, "drop_off_step": None}
        except Exception as e:
            logger.error(f"[MOLMO] Funnel tracking failed: {e}", exc_info=True)
            return {"steps": [], "completed": False, "drop_off_step": None, "error": str(e)}

    def analyze(self, video_url: str) -> Dict[str, Any]:
        """
        Run full analysis pipeline on video via OpenRouter API.

        Args:
            video_url: Publicly accessible URL to video file
                      Note: The video must be accessible without authentication.
                      Supabase public buckets work, but signed URLs may expire.

        Returns:
            Structured dict with all analysis results
        """
        if not settings.molmo_enabled:
            logger.info("[MOLMO] Analysis disabled in config")
            return {}

        # Verify URL is accessible (basic check)
        if not video_url or not video_url.startswith(("http://", "https://")):
            raise ValueError(f"Invalid video URL: {video_url}. Must be a publicly accessible HTTP(S) URL.")

        logger.info(f"[MOLMO] Starting analysis for video: {video_url}")

        # Run all analysis tasks (continue even if some fail)
        summary = ""
        interactions = {"clicks": [], "hovers": [], "scrolls": []}
        counts = {}
        errors = []
        funnel = {"steps": [], "completed": False, "drop_off_step": None}

        try:
            summary = self._dense_caption(video_url)
        except Exception as e:
            logger.error(f"[MOLMO] Dense caption failed: {e}")
            summary = f"Failed to generate summary: {str(e)}"

        try:
            interactions = self._detect_interactions(video_url)
        except Exception as e:
            logger.error(f"[MOLMO] Interaction detection failed: {e}")
            interactions = {"clicks": [], "hovers": [], "scrolls": [], "error": str(e)}

        try:
            counts = self._count_actions(video_url)
        except Exception as e:
            logger.error(f"[MOLMO] Action counting failed: {e}")
            counts = {"error": str(e)}

        try:
            errors = self._detect_errors(video_url)
        except Exception as e:
            logger.error(f"[MOLMO] Error detection failed: {e}")
            errors = [{"type": "analysis_error", "description": str(e), "timestamp_ms": 0}]

        try:
            funnel = self._track_funnel(video_url)
        except Exception as e:
            logger.error(f"[MOLMO] Funnel tracking failed: {e}")
            funnel = {"steps": [], "completed": False, "drop_off_step": None, "error": str(e)}

        # If all tasks failed, raise an exception
        if (not summary or "error" in str(summary).lower()) and \
           interactions.get("error") and \
           counts.get("error") and \
           funnel.get("error"):
            raise Exception("All analysis tasks failed")

        return {
            "session_summary": summary,
            "interaction_heatmap": interactions,
            "action_counts": counts,
            "error_events": errors,
            "conversion_funnel": funnel,
        }
