from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Callable
import os
import datetime


class Downloader(ABC):
    """Abstract base class for downloaders."""

    @abstractmethod
    async def download_file(
        self,
        url: str,
        output_path: str,
        verify_checksum: bool = True,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> bool:
        """Download a file from the specified URL.

        Args:
            url (str): URL to download from
            output_path (str): Path to save the file to
            verify_checksum (bool, optional): Whether to verify the checksum. Defaults to True.
            progress_callback (Optional[Callable[[int, int], None]], optional):
                Callback for progress updates. Receives bytes downloaded and total bytes. Defaults to None.

        Returns:
            bool: True if download was successful, False otherwise
        """
        pass

    @abstractmethod
    async def download_files(
        self,
        urls: List[str],
        output_dir: str,
        verify_checksum: bool = True,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        max_concurrent_downloads: int = 5,
    ) -> Dict[str, bool]:
        """Download multiple files from the specified URLs.

        Args:
            urls (List[str]): URLs to download from
            output_dir (str): Directory to save the files to
            verify_checksum (bool, optional): Whether to verify the checksum. Defaults to True.
            progress_callback (Optional[Callable[[int, int, str], None]], optional):
                Callback for progress updates. Receives files completed, total files, and current file. Defaults to None.
            max_concurrent_downloads (int, optional): Maximum number of concurrent downloads. Defaults to 5.

        Returns:
            Dict[str, bool]: Dictionary mapping URLs to download success status
        """
        pass

    @abstractmethod
    def set_proxy(self, proxy: Optional[str]) -> None:
        """Set the proxy to use for downloads.

        Args:
            proxy (Optional[str]): Proxy URL or None to disable proxy
        """
        pass

    @abstractmethod
    def set_retry_count(self, retry_count: int) -> None:
        """Set the number of times to retry failed downloads.

        Args:
            retry_count (int): Number of retries
        """
        pass

    @abstractmethod
    def filter_files_by_date_range(
        self,
        files: List[str],
        start_date: Optional[datetime.date] = None,
        end_date: Optional[datetime.date] = None,
    ) -> List[str]:
        """Filter files by date range.

        Args:
            files (List[str]): List of file paths or URLs
            start_date (Optional[datetime.date], optional): Start date (inclusive). Defaults to None.
            end_date (Optional[datetime.date], optional): End date (inclusive). Defaults to None.

        Returns:
            List[str]: Filtered list of file paths or URLs
        """
        pass

    @abstractmethod
    async def extract_files(
        self,
        source_dir: str,
        extract_dir: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        max_concurrent_extractions: int = 5,
    ) -> Dict[str, bool]:
        """Extract downloaded zip files asynchronously.

        Args:
            source_dir (str): Directory containing the downloaded zip files
            extract_dir (Optional[str], optional): Directory to extract files to.
                If None, will create a directory with the same structure as source_dir
                but with '_extracted' suffix. Defaults to None.
            progress_callback (Optional[Callable[[int, int, str], None]], optional):
                Callback for progress updates. Receives files completed, total files, and current file.
            max_concurrent_extractions (int, optional): Maximum number of concurrent extractions. Defaults to 5.

        Returns:
            Dict[str, bool]: Dictionary mapping file paths to extraction success status
        """
        pass
