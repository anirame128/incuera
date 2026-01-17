"""Supabase Storage service for video file uploads."""
import os
import httpx
from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote
from app.config import settings
from app.utils.logger import logger


@dataclass
class UploadResult:
    """Result of a file upload operation."""
    success: bool
    url: Optional[str] = None
    error: Optional[str] = None


class StorageService:
    """Service for uploading files to Supabase Storage using the REST API."""

    BUCKET_NAME = "session-videos"

    def __init__(self):
        self.supabase_url = settings.supabase_url
        self.supabase_key = settings.supabase_secret_key
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError(
                "Supabase URL and secret key must be configured. "
                "Set SUPABASE_URL and SUPABASE_SECRET_KEY environment variables."
            )
        
        # Ensure URL doesn't have trailing slash
        self.supabase_url = self.supabase_url.rstrip('/')
        self.storage_url = f"{self.supabase_url}/storage/v1"
        self._bucket_checked = False
        self._bucket_public = None  # Cache bucket public status

    async def _ensure_bucket_exists(self) -> bool:
        """Ensure the storage bucket exists, create it if it doesn't."""
        if self._bucket_checked:
            return True
        
        try:
            headers = {
                "apikey": self.supabase_key,
                "Authorization": f"Bearer {self.supabase_key}",
                "Content-Type": "application/json",
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Check if bucket exists
                check_url = f"{self.storage_url}/bucket/{self.BUCKET_NAME}"
                check_response = await client.get(check_url, headers=headers)
                
                if check_response.status_code == 200:
                    # Bucket exists, check if it's public
                    bucket_data = check_response.json()
                    self._bucket_public = bucket_data.get("public", False)
                    self._bucket_checked = True
                    return True
                
                # Bucket doesn't exist, create it
                if check_response.status_code == 404:
                    create_url = f"{self.storage_url}/bucket"
                    create_response = await client.post(
                        create_url,
                        headers=headers,
                        json={
                            "id": self.BUCKET_NAME,
                            "name": self.BUCKET_NAME,
                            "public": True,  # Public bucket so videos can be accessed via URL
                        },
                    )
                    
                    if create_response.status_code in [200, 201]:
                        self._bucket_public = True
                        self._bucket_checked = True
                        return True
                    else:
                        error_text = create_response.text
                        logger.error(
                            f"Failed to create bucket {self.BUCKET_NAME}: "
                            f"{create_response.status_code} - {error_text}"
                        )
                        return False
                
                # Other error
                logger.error(
                    f"Failed to check bucket {self.BUCKET_NAME}: "
                    f"{check_response.status_code} - {check_response.text}"
                )
                return False
                
        except Exception as e:
            logger.error(f"Error ensuring bucket exists: {e}", exc_info=True)
            return False

    async def upload_file(
        self,
        file_path: str,
        storage_path: str,
        content_type: Optional[str] = None,
    ) -> UploadResult:
        """
        Upload a file to Supabase Storage using the REST API.

        Args:
            file_path: Local path to the file
            storage_path: Path in storage bucket (e.g., "videos/{project_id}/{session_id}/replay.mp4")
            content_type: MIME type of the file

        Returns:
            UploadResult with success status and public URL
        """
        try:
            # Ensure bucket exists before uploading
            if not await self._ensure_bucket_exists():
                return UploadResult(
                    success=False,
                    error=f"Storage bucket '{self.BUCKET_NAME}' does not exist and could not be created. "
                    f"Please create it manually in the Supabase Dashboard."
                )
            
            if not os.path.exists(file_path):
                return UploadResult(
                    success=False,
                    error=f"File not found: {file_path}"
                )

            # Determine content type from extension if not provided
            if content_type is None:
                content_type = self._get_content_type(file_path)

            # Correctly format the URL for file upload
            # Note: storage_path might contain slashes which are part of the path structure
            # We should NOT quote slash characters as they define the directory structure
            # But we should quote other special characters
            
            # For the object path, we need to handle each segment
            # e.g. videos/project_id/session_id/replay.mp4
            # We only quote the segments, not the slashes
            path_segments = storage_path.split('/')
            encoded_segments = [quote(segment, safe='') for segment in path_segments]
            encoded_path = '/'.join(encoded_segments)
            
            upload_url = f"{self.storage_url}/object/{self.BUCKET_NAME}/{encoded_path}"

            # Read file content
            with open(file_path, "rb") as f:
                file_content = f.read()

            # Upload to Supabase Storage using REST API
            # For secret keys (sb_secret_...), use apikey header
            # The API Gateway handles authentication for secret keys
            headers = {
                "apikey": self.supabase_key,
                "Authorization": f"Bearer {self.supabase_key}",
                "Content-Type": content_type,
                "x-upsert": "true",  # Enable upsert for overwriting existing files
            }

            async with httpx.AsyncClient(timeout=60.0) as client:
                logger.error(f"[STORAGE] Uploading to URL: {upload_url}, file size: {len(file_content)} bytes")
                response = await client.post(
                    upload_url,
                    headers=headers,
                    content=file_content,
                )

                logger.error(f"[STORAGE] Upload response status: {response.status_code}")
                if response.status_code not in [200, 201]:
                    error_text = response.text
                    logger.error(
                        f"[STORAGE] Storage upload failed: {response.status_code} - {error_text}"
                    )
                    return UploadResult(
                        success=False,
                        error=f"Upload failed: {response.status_code} - {error_text}"
                    )
                logger.error(f"[STORAGE] Upload successful, response: {response.text[:200]}")

            # Generate URL based on bucket type
            if self._bucket_public:
                # Public bucket - use public URL
                # Similar encoding logic: preserve slashes, encode segments
                path_segments = storage_path.split('/')
                encoded_segments = [quote(segment, safe='') for segment in path_segments]
                encoded_path = '/'.join(encoded_segments)
                
                file_url = f"{self.storage_url}/object/public/{self.BUCKET_NAME}/{encoded_path}"
                logger.error(f"[STORAGE] Generated public URL: {file_url}")
            else:
                # Private bucket - generate signed URL (valid for 1 year)
                logger.error(f"[STORAGE] Bucket is private, generating signed URL")
                file_url = await self._create_signed_url(storage_path, expires_in=31536000)  # 1 year
                if not file_url:
                    logger.error(f"[STORAGE] Failed to generate signed URL")
                    return UploadResult(
                        success=False,
                        error="Failed to generate signed URL for private bucket"
                    )
                logger.error(f"[STORAGE] Generated signed URL: {file_url}")

            return UploadResult(success=True, url=file_url)

        except Exception as e:
            logger.error(f"Failed to upload file {file_path} to {storage_path}: {e}", exc_info=True)
            return UploadResult(success=False, error=str(e))

    async def upload_video(
        self,
        video_path: str,
        project_id: str,
        session_id: str,
    ) -> UploadResult:
        """Upload a video file."""
        logger.error(f"[STORAGE] Uploading video: {video_path} for project {project_id}, session {session_id}")
        # Determine extension from the source file
        ext = os.path.splitext(video_path)[1].lower() or ".webm"
        content_type = "video/webm" if ext == ".webm" else "video/mp4"
        storage_path = f"videos/{project_id}/{session_id}/replay{ext}"
        logger.error(f"[STORAGE] Storage path: {storage_path}, content_type: {content_type}")
        result = await self.upload_file(video_path, storage_path, content_type)
        if result.success:
            logger.error(f"[STORAGE] Video upload successful: {result.url}")
        else:
            logger.error(f"[STORAGE] Video upload failed: {result.error}")
        return result

    async def upload_thumbnail(
        self,
        thumbnail_path: str,
        project_id: str,
        session_id: str,
    ) -> UploadResult:
        """Upload a thumbnail image."""
        storage_path = f"videos/{project_id}/{session_id}/thumbnail.jpg"
        return await self.upload_file(thumbnail_path, storage_path, "image/jpeg")

    async def upload_keyframes(
        self,
        keyframes_path: str,
        project_id: str,
        session_id: str,
    ) -> UploadResult:
        """Upload keyframes JSON."""
        storage_path = f"videos/{project_id}/{session_id}/keyframes.json"
        return await self.upload_file(keyframes_path, storage_path, "application/json")

    async def _create_signed_url(self, storage_path: str, expires_in: int = 3600) -> Optional[str]:
        """Create a signed URL for a file in a private bucket."""
        try:
            encoded_path = quote(storage_path, safe='')
            sign_url = f"{self.storage_url}/object/sign/{self.BUCKET_NAME}/{encoded_path}"
            
            headers = {
                "apikey": self.supabase_key,
                "Authorization": f"Bearer {self.supabase_key}",
                "Content-Type": "application/json",
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    sign_url,
                    headers=headers,
                    json={"expiresIn": expires_in},
                )
                
                if response.status_code == 200:
                    data = response.json()
                    signed_path = data.get("signedURL", "")
                    # Construct full URL
                    if signed_path.startswith("/"):
                        return f"{self.supabase_url}{signed_path}"
                    return signed_path
                else:
                    logger.error(f"Failed to create signed URL: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error creating signed URL: {e}", exc_info=True)
            return None

    def _get_content_type(self, file_path: str) -> str:
        """Get content type from file extension."""
        ext = os.path.splitext(file_path)[1].lower()
        content_types = {
            ".mp4": "video/mp4",
            ".webm": "video/webm",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".json": "application/json",
            ".zip": "application/zip",
        }
        return content_types.get(ext, "application/octet-stream")


# Singleton instance
storage_service = StorageService()
