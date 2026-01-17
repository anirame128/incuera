"""Video generation service using Playwright's native video recording."""
import asyncio
import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from app.config import settings
from app.utils.logger import logger
import urllib.request
from functools import lru_cache


@dataclass
class VideoResult:
    """Result of video generation."""
    success: bool
    video_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    keyframes_path: Optional[str] = None
    duration_ms: int = 0
    size_bytes: int = 0
    error: Optional[str] = None


# HTML template for rrweb player
# Using rrweb 1.x which has stable, well-tested browser builds

# HTML template for rrweb player
# We embed the assets directly to avoid network issues and parsing blocking in headless mode
PLAYER_HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Session Replay</title>
    <style>
        {style_content}
        
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        html, body {{
            width: 100%;
            height: 100%;
            background: #f5f5f5;
            overflow: hidden;
        }}
        #player-container {{
            width: 100%;
            height: 100%;
            display: flex;
            justify-content: center;
            align-items: center;
        }}
        .rr-player {{
            background: white;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        .rr-controller {{
            display: none !important;
        }}
    </style>
</head>
<body>
    <div id="player-container"></div>

    <script>
        {script_content}
    </script>

    <script>
        window.pageReady = false;
        window.loadError = null;

        // Check for rrwebPlayer global
        var checkCount = 0;
        function checkReady() {{
            checkCount++;
            console.log('Check #' + checkCount + ': rrwebPlayer=' + (typeof rrwebPlayer));

            if (typeof rrwebPlayer !== 'undefined') {{
                window.pageReady = true;
                console.log('rrweb-player loaded successfully');
                return;
            }}

            // Also check for default export pattern
            if (typeof window.rrwebPlayer !== 'undefined') {{
                window.pageReady = true;
                console.log('rrweb-player loaded (window.rrwebPlayer)');
                return;
            }}

            if (checkCount < 100) {{
                setTimeout(checkReady, 100);
            }} else {{
                window.loadError = 'Timeout waiting for rrwebPlayer to load';
                console.error(window.loadError);
            }}
        }}

        // Start checking after a brief delay to let scripts initialize
        setTimeout(checkReady, 500);

        window.startPlayback = function(events) {{
            console.log('startPlayback called with ' + events.length + ' events');

            if (!events || events.length === 0) {{
                console.error('No events provided');
                return false;
            }}

            try {{
                var PlayerClass = rrwebPlayer;
                if (PlayerClass.default) {{
                    PlayerClass = PlayerClass.default;
                }}

                var player = new PlayerClass({{
                    target: document.getElementById('player-container'),
                    props: {{
                        events: events,
                        width: 1280,
                        height: 720,
                        autoPlay: true,
                        showController: false,
                        skipInactive: true,
                        speed: 1
                    }}
                }});

                window.playerInstance = player;
                console.log('Player created successfully');
                return true;
            }} catch (e) {{
                console.error('Failed to create player:', e.message);
                window.loadError = e.message;
                return false;
            }}
        }};
    </script>
</body>
</html>
"""


class VideoGenerator:
    """Generates videos from rrweb session events using Playwright's native recording."""

    def __init__(
        self,
        width: int = None,
        height: int = None,
        max_duration_seconds: int = None,
    ):
        self.width = width or settings.video_resolution_width
        self.height = height or settings.video_resolution_height
        self.max_duration_seconds = max_duration_seconds or settings.video_max_duration_seconds

    @staticmethod
    @lru_cache(maxsize=1)
    def _load_static_assets() -> tuple[str, str]:
        """
        Load rrweb-player static assets (JS and CSS).
        Uses caching to avoid fetching on every request.
        """
        version = "1.0.0-alpha.4"  # Use a stable version that exists
        base_url = f"https://cdn.jsdelivr.net/npm/rrweb-player@{version}/dist"
        
        try:
            logger.info(f"Fetching rrweb-player assets from {base_url}...")
            
            # Fetch JS
            with urllib.request.urlopen(f"{base_url}/index.js") as response:
                script_content = response.read().decode('utf-8')
                
            # Fetch CSS
            with urllib.request.urlopen(f"{base_url}/style.css") as response:
                style_content = response.read().decode('utf-8')
                
            logger.info("Successfully fetched rrweb-player assets")
            return script_content, style_content
            
        except Exception as e:
            logger.error(f"Failed to fetch rrweb-player assets: {e}")
            # Fallback to empty strings or throw error
            # In production, we might want to have these files locally as fallback
            raise e

    async def generate_video(
        self,
        events: List[Dict[str, Any]],
        output_dir: str,
        session_id: str,
    ) -> VideoResult:
        """
        Generate a video from rrweb events using Playwright's native video recording.

        Args:
            events: List of rrweb event dictionaries
            output_dir: Directory to store output files
            session_id: Session identifier for naming

        Returns:
            VideoResult with paths to generated files
        """
        if not events:
            return VideoResult(success=False, error="No events provided")

        temp_dir = None
        try:
            # Create temporary directories
            temp_dir = tempfile.mkdtemp(prefix=f"video_{session_id}_")
            temp_video_dir = os.path.join(temp_dir, "recordings")
            os.makedirs(temp_video_dir, exist_ok=True)
            os.makedirs(output_dir, exist_ok=True)

            # Calculate duration from events
            timestamps = [e.get("timestamp", 0) for e in events]
            start_time = min(timestamps)
            end_time = max(timestamps)
            duration_ms = end_time - start_time
            duration_sec = duration_ms / 1000

            # Add buffer time for loading and ending
            total_duration = min(duration_sec + 3, self.max_duration_seconds)

            logger.info(f"Rendering {total_duration:.2f} seconds of video for session {session_id}")

            # Use Playwright to record the video
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        "--disable-web-security",
                        "--disable-features=IsolateOrigins,site-per-process",
                    ]
                )
                context = await browser.new_context(
                    record_video_dir=temp_video_dir,
                    record_video_size={"width": self.width, "height": self.height},
                    viewport={"width": self.width, "height": self.height},
                )
                page = await context.new_page()

                # Capture browser console logs for debugging
                page.on("console", lambda msg: logger.debug(f"Browser console [{msg.type}]: {msg.text}"))
                page.on("pageerror", lambda err: logger.error(f"Browser page error: {err}"))

                # Load static assets
                try:
                    script_content, style_content = self._load_static_assets()
                    html_content = PLAYER_HTML_TEMPLATE.format(
                        script_content=script_content,
                        style_content=style_content
                    )
                except Exception as e:
                    return VideoResult(success=False, error=f"Failed to load player assets: {e}")

                # Load the player HTML using set_content (more reliable than file://)
                # This allows the page to load external scripts from CDN
                await page.set_content(html_content, wait_until="networkidle")
                logger.info("Loaded player HTML via set_content")

                # Wait for rrwebPlayer library to load
                try:
                    await page.wait_for_function(
                        "() => window.pageReady === true || window.loadError !== null",
                        timeout=30000
                    )

                    # Check if there was an error
                    load_error = await page.evaluate("() => window.loadError")
                    if load_error:
                        logger.error(f"rrweb-player load error: {load_error}")
                        await context.close()
                        await browser.close()
                        return VideoResult(success=False, error=f"Failed to load replay player: {load_error}")

                    logger.info("rrweb-player library loaded successfully")
                except Exception as e:
                    # Try to get any error info from the page
                    try:
                        load_error = await page.evaluate("() => window.loadError")
                        logger.error(f"Load error from page: {load_error}")
                    except:
                        pass
                    logger.error(f"Timeout waiting for rrweb-player: {e}")
                    await context.close()
                    await browser.close()
                    return VideoResult(success=False, error="Failed to load replay player - timeout")

                # Start playback with events
                logger.info(f"Starting playback with {len(events)} events")
                playback_result = await page.evaluate(f"startPlayback({json.dumps(events)})")

                # Wait for playback to complete
                await asyncio.sleep(total_duration)

                # Close context to finalize video
                await context.close()
                await browser.close()

            # Find the recorded video
            video_files = os.listdir(temp_video_dir)
            if not video_files:
                return VideoResult(success=False, error="No video file generated")

            # Get the latest video file
            latest_video = max(
                [os.path.join(temp_video_dir, f) for f in video_files if f.endswith(".webm")],
                key=os.path.getctime
            )

            # Move to output directory
            output_video_path = os.path.join(output_dir, "replay.webm")
            shutil.move(latest_video, output_video_path)

            # Generate thumbnail from first frame
            thumbnail_path = os.path.join(output_dir, "thumbnail.jpg")
            await self._generate_thumbnail(output_video_path, thumbnail_path)

            # Get file size
            video_size = os.path.getsize(output_video_path)

            logger.info(f"Video generated: {output_video_path} ({video_size} bytes)")

            # Store the actual rendered video duration (includes buffer time)
            actual_duration_ms = int(total_duration * 1000)

            return VideoResult(
                success=True,
                video_path=output_video_path,
                thumbnail_path=thumbnail_path if os.path.exists(thumbnail_path) else None,
                duration_ms=actual_duration_ms,
                size_bytes=video_size,
            )

        except Exception as e:
            logger.error(f"Video generation failed: {e}", exc_info=True)
            return VideoResult(success=False, error=str(e))
        finally:
            # Cleanup temporary directory
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)

    async def _generate_thumbnail(self, video_path: str, output_path: str):
        """Generate thumbnail from first frame of video using ffmpeg."""
        try:
            import subprocess

            cmd = [
                "ffmpeg",
                "-y",
                "-i", video_path,
                "-vframes", "1",
                "-vf", f"scale={320}:-1",
                "-q:v", "2",
                output_path,
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await process.communicate()
        except Exception as e:
            logger.warning(f"Failed to generate thumbnail: {e}")
