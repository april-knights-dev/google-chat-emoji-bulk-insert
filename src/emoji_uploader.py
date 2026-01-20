"""Google Chat custom emoji upload module."""

import base64
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials


@dataclass
class UploadResult:
    """Result of emoji upload attempt."""
    success: bool
    emoji_name: str
    file_path: str
    error: Optional[str] = None
    resource_name: Optional[str] = None

    def __str__(self) -> str:
        if self.success:
            return f"[SUCCESS] {self.emoji_name}"
        return f"[FAILED] {self.emoji_name}: {self.error}"


class EmojiUploader:
    """Handles uploading custom emojis to Google Chat."""

    def __init__(self, credentials: Credentials):
        """
        Initialize the uploader with credentials.

        Args:
            credentials: Valid Google OAuth2 credentials
        """
        self.service = build('chat', 'v1', credentials=credentials)

    def _get_mime_type(self, file_path: str) -> str:
        """Get MIME type based on file extension."""
        ext = Path(file_path).suffix.lower()
        mime_types = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
        }
        return mime_types.get(ext, 'image/png')

    def _encode_image(self, file_path: str) -> str:
        """Read and base64 encode an image file."""
        with open(file_path, 'rb') as f:
            return base64.standard_b64encode(f.read()).decode('utf-8')

    def upload_emoji(self, file_path: str, emoji_name: str, retry_count: int = 3) -> UploadResult:
        """
        Upload a single emoji to Google Chat.

        Args:
            file_path: Path to the emoji image file
            emoji_name: Name for the emoji (without colons)
            retry_count: Number of retries on transient errors

        Returns:
            UploadResult with upload status
        """
        for attempt in range(retry_count):
            try:
                # Prepare the request body
                image_data = self._encode_image(file_path)
                mime_type = self._get_mime_type(file_path)

                body = {
                    'customEmoji': {
                        'shortcode': emoji_name,
                        'payload': {
                            'fileContent': image_data,
                            'mimeType': mime_type,
                        }
                    }
                }

                # Call the API
                result = self.service.customEmojis().create(body=body).execute()

                return UploadResult(
                    success=True,
                    emoji_name=emoji_name,
                    file_path=file_path,
                    resource_name=result.get('name')
                )

            except HttpError as e:
                error_msg = str(e)

                # Don't retry on client errors (4xx)
                if e.resp.status >= 400 and e.resp.status < 500:
                    return UploadResult(
                        success=False,
                        emoji_name=emoji_name,
                        file_path=file_path,
                        error=f"API error ({e.resp.status}): {error_msg}"
                    )

                # Retry on server errors (5xx)
                if attempt < retry_count - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    time.sleep(wait_time)
                    continue

                return UploadResult(
                    success=False,
                    emoji_name=emoji_name,
                    file_path=file_path,
                    error=f"API error after {retry_count} retries: {error_msg}"
                )

            except Exception as e:
                return UploadResult(
                    success=False,
                    emoji_name=emoji_name,
                    file_path=file_path,
                    error=str(e)
                )

        return UploadResult(
            success=False,
            emoji_name=emoji_name,
            file_path=file_path,
            error="Unknown error"
        )

    def list_existing_emojis(self) -> set[str]:
        """
        List all existing custom emojis.

        Returns:
            Set of existing emoji names
        """
        existing = set()
        page_token = None

        try:
            while True:
                request = self.service.customEmojis().list(pageSize=100, pageToken=page_token)
                response = request.execute()

                for emoji in response.get('customEmojis', []):
                    existing.add(emoji.get('shortcode', ''))

                page_token = response.get('nextPageToken')
                if not page_token:
                    break

        except HttpError as e:
            print(f"Warning: Could not list existing emojis: {e}")

        return existing
