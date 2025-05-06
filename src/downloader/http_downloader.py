import os
import asyncio
import httpx
import datetime
import re
import zipfile
import shutil
from typing import List, Dict, Any, Optional, Callable, Tuple
import aiofiles
from loguru import logger
import sys


from .base import Downloader
from .checksum import CheckSum


class HttpDownloader(Downloader):
    """HTTP downloader implementation."""

    def __init__(self, retry_count: int = 3, proxy: Optional[str] = None):
        """Initialize the HTTP downloader.

        Args:
            retry_count (int, optional): Number of retries for failed downloads. Defaults to 3.
            proxy (Optional[str], optional): Proxy URL or None to disable proxy. Defaults to None.
        """
        self.retry_count = retry_count
        self.proxy = proxy
        self.checksum_verifier = CheckSum()

    def set_proxy(self, proxy: Optional[str]) -> None:
        """Set the proxy to use for downloads.

        Args:
            proxy (Optional[str]): Proxy URL or None to disable proxy
        """
        self.proxy = proxy

    def set_retry_count(self, retry_count: int) -> None:
        """Set the number of times to retry failed downloads.

        Args:
            retry_count (int): Number of retries
        """
        self.retry_count = retry_count

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
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        client_kwargs = {}
        client_kwargs["timeout"] = httpx.Timeout(30.0, connect=30.0)

        if self.proxy:
            client_kwargs["proxy"] = self.proxy

        for attempt in range(self.retry_count + 1):
            try:
                async with httpx.AsyncClient(**client_kwargs) as client:
                    # Start the request
                    async with client.stream("GET", url) as response:
                        response.raise_for_status()

                        # Get the total size if available
                        total_size = int(response.headers.get("Content-Length", 0))

                        # Open the output file
                        async with aiofiles.open(output_path, "wb") as f:
                            downloaded_size = 0

                            # Download the file in chunks
                            async for chunk in response.aiter_bytes(chunk_size=8192):
                                await f.write(chunk)
                                downloaded_size += len(chunk)

                                # Update progress if callback is provided
                                if progress_callback:
                                    progress_callback(downloaded_size, total_size)

                if verify_checksum and not url.endswith(".CHECKSUM"):
                    checksum_url = f"{url}.CHECKSUM"
                    checksum_path = f"{output_path}.CHECKSUM"

                    try:
                        async with httpx.AsyncClient(**client_kwargs) as client:
                            checksum_response = await client.get(checksum_url)
                            checksum_response.raise_for_status()

                            async with aiofiles.open(checksum_path, "wb") as f:
                                await f.write(checksum_response.content)

                        # Verify the checksum
                        if not self.checksum_verifier.verify_checksum(output_path):
                            logger.warning(
                                f"Checksum verification failed for {url}, retrying download..."
                            )
                            # Delete the failed files
                            if os.path.exists(output_path):
                                os.remove(output_path)
                            if os.path.exists(checksum_path):
                                os.remove(checksum_path)
                            # Continue to the next attempt
                            continue
                    except (httpx.HTTPError, httpx.TimeoutException) as e:
                        logger.error(
                            f"Failed to download checksum file: {checksum_url}, retrying download..."
                        )
                        continue

                return True

            except (httpx.HTTPError, httpx.TimeoutException, asyncio.TimeoutError) as e:
                logger.error(
                    f"HTTP error occurred on attempt {attempt + 1}/{self.retry_count + 1}, url: {url}"
                )

                if attempt < self.retry_count:
                    wait_time = 2**attempt
                    logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        f"Failed to download {url} after {self.retry_count + 1} attempts"
                    )
                    return False

        return False

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
        os.makedirs(output_dir, exist_ok=True)

        semaphore = asyncio.Semaphore(max_concurrent_downloads)

        results = {}

        tasks = []

        # Create a counter for completed files
        completed_files = 0
        total_files = len(urls)

        async def download_with_semaphore(url: str) -> Tuple[str, bool]:
            nonlocal completed_files

            # Extract the filename from the URL
            filename = os.path.basename(url)
            output_path = os.path.join(output_dir, filename)

            # Define a progress callback for this file
            def file_progress_callback(downloaded: int, total: int) -> None:
                if progress_callback:
                    progress_percentage = ""
                    if total > 0:
                        percentage = min(100, int(downloaded * 100 / total))
                        progress_percentage = f" ({percentage}%)"

                    progress_callback(
                        0,  # 0 indicates this is not a completion update
                        total_files,
                        f"{url}{progress_percentage}",
                    )

            async with semaphore:
                success = await self.download_file(
                    url=url,
                    output_path=output_path,
                    verify_checksum=verify_checksum,
                    progress_callback=file_progress_callback,
                )

                if progress_callback:
                    completed_files += 1

                    # Call the progress callback with the completed count
                    # The completed count > 0 signals that this is a completion update
                    progress_callback(completed_files, total_files, url)

                return url, success

        # Task downloading each file
        for url in urls:
            task = asyncio.create_task(download_with_semaphore(url))
            tasks.append(task)

        for task in asyncio.as_completed(tasks):
            url, success = await task
            results[url] = success

        return results

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
        if not start_date and not end_date:
            logger.debug("No date range specified, returning all files")
            return files

        logger.debug(
            f"Filtering {len(files)} files by date range: {start_date} to {end_date}"
        )
        filtered_files = []
        excluded_files = []

        for file in files:
            filename = file.split("/")[-1]
            full_date_match = re.search(r"(\d{4}-\d{2}-\d{2})", filename)
            year_month_match = re.search(r"(\d{4}-\d{2})", filename)

            if full_date_match:
                # full date (YYYY-MM-DD)
                file_date_str = full_date_match.group(1)
                try:
                    file_date = datetime.datetime.strptime(
                        file_date_str, "%Y-%m-%d"
                    ).date()

                    if start_date and file_date < start_date:
                        logger.debug(
                            f"Excluding {filename}: date {file_date} is before start date {start_date}"
                        )
                        excluded_files.append(file)
                        continue
                    if end_date and file_date > end_date:
                        logger.debug(
                            f"Excluding {filename}: date {file_date} is after end date {end_date}"
                        )
                        excluded_files.append(file)
                        continue

                    logger.debug(
                        f"Including {filename}: date {file_date} is within range"
                    )
                    filtered_files.append(file)
                except ValueError:
                    logger.debug(
                        f"Including {filename}: date parsing failed for {file_date_str}"
                    )
                    filtered_files.append(file)
            elif year_month_match:
                # year-month format (YYYY-MM)
                file_date_str = year_month_match.group(1)
                try:
                    # For year-month format, use the first day of the month
                    file_date = datetime.datetime.strptime(
                        f"{file_date_str}-01", "%Y-%m-%d"
                    ).date()

                    # For end date comparison with year-month format, we need to check if any day in the month is within range
                    # Get the last day of the month
                    if file_date.month == 12:
                        last_day = datetime.date(
                            file_date.year + 1, 1, 1
                        ) - datetime.timedelta(days=1)
                    else:
                        last_day = datetime.date(
                            file_date.year, file_date.month + 1, 1
                        ) - datetime.timedelta(days=1)

                    # Check if any part of the month is within the date range
                    if start_date and last_day < start_date:
                        logger.debug(
                            f"Excluding {filename}: month {file_date_str} is before start date {start_date}"
                        )
                        excluded_files.append(file)
                        continue
                    if end_date and file_date > end_date:
                        logger.debug(
                            f"Excluding {filename}: month {file_date_str} is after end date {end_date}"
                        )
                        excluded_files.append(file)
                        continue

                    logger.debug(
                        f"Including {filename}: month {file_date_str} is within range"
                    )
                    filtered_files.append(file)
                except ValueError:
                    logger.debug(
                        f"Including {filename}: date parsing failed for {file_date_str}"
                    )
                    filtered_files.append(file)
            else:
                # If no date pattern is found, include the file
                logger.debug(f"Including {filename}: no date pattern found")
                filtered_files.append(file)

        logger.debug(
            f"Date filtering results: {len(filtered_files)} included, {len(excluded_files)} excluded"
        )
        return filtered_files

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
        # Find all zip files in the source directory
        zip_files = []
        for root, _, files in os.walk(source_dir):
            for file in files:
                if file.endswith(".zip") and not file.endswith(".CHECKSUM"):
                    zip_files.append(os.path.join(root, file))

        if not zip_files:
            logger.warning(f"No zip files found in {source_dir}")
            return {}

        # Determine the extraction directory
        if extract_dir is None:
            # Create a directory with the same structure but with '_extracted' suffix
            parent_dir = os.path.dirname(source_dir)
            base_name = os.path.basename(source_dir)
            extract_dir = os.path.join(parent_dir, f"{base_name}_extracted")

        # Create the extraction directory if it doesn't exist
        os.makedirs(extract_dir, exist_ok=True)

        # Create a semaphore to limit concurrent extractions
        semaphore = asyncio.Semaphore(max_concurrent_extractions)

        # Extract each zip file
        results = {}
        total_files = len(zip_files)
        completed_files = 0

        # First call progress_callback with total files to initialize the progress bar
        if progress_callback and total_files > 0:
            # Call with 0 completed files to initialize
            progress_callback(0, total_files, "Initializing extraction...")

        async def extract_zip_file(zip_path: str) -> Tuple[str, bool]:
            """Extract a single zip file asynchronously.

            Args:
                zip_path (str): Path to the zip file to extract

            Returns:
                Tuple[str, bool]: Tuple of (zip_path, success)
            """
            nonlocal completed_files

            try:
                # Determine the relative path from the source directory
                rel_path = os.path.relpath(zip_path, source_dir)
                # Create the corresponding directory in the extraction directory
                extract_subdir = os.path.join(extract_dir, os.path.dirname(rel_path))
                os.makedirs(extract_subdir, exist_ok=True)

                # Update progress with current file name
                if progress_callback:
                    # Still use 0 for completed files to indicate this is just a description update
                    progress_callback(
                        0, total_files, f"Extracting {os.path.basename(zip_path)}"
                    )

                # Use a semaphore to limit concurrent extractions
                async with semaphore:
                    # Run the CPU-bound extraction in a thread pool
                    await asyncio.to_thread(self._extract_zip, zip_path, extract_subdir)

                # Update progress with completion
                completed_files += 1
                if progress_callback:
                    progress_callback(completed_files, total_files, zip_path)

                return zip_path, True

            except Exception as e:
                logger.error(f"Failed to extract {zip_path}: {e}")
                return zip_path, False

        # Create tasks for all zip files
        tasks = [asyncio.create_task(extract_zip_file(zip_path)) for zip_path in zip_files]

        # Wait for all tasks to complete
        for task in asyncio.as_completed(tasks):
            zip_path, success = await task
            results[zip_path] = success

        return results

    def _extract_zip(self, zip_path: str, extract_dir: str) -> None:
        """Extract a zip file to the specified directory.

        This is a synchronous method that will be run in a thread pool.

        Args:
            zip_path (str): Path to the zip file to extract
            extract_dir (str): Directory to extract the zip file to
        """
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_dir)
