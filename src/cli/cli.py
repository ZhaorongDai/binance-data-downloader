import os
import sys
import asyncio
import datetime
import re
from typing import List, Dict, Optional, Tuple
import argparse
from loguru import logger
from tqdm import tqdm

from ..directory_tree.base import DirectoryTreeProvider
from ..directory_tree.binance import BinanceDirectoryTreeProvider
from ..downloader.base import Downloader
from ..downloader.http_downloader import HttpDownloader


class CliApp:
    """Command-line interface for the cryptocurrency data downloader."""

    def __init__(self):
        """Initialize the CLI application."""
        self.directory_tree_provider = BinanceDirectoryTreeProvider()
        self.downloader = HttpDownloader()
        self.download_url_prefix = (
            self.directory_tree_provider.get_download_url_prefix()
        )

    def _setup_logger(self, log_level: str = "INFO"):
        """Set up the logger.

        Args:
            log_level (str, optional): Log level. Defaults to "INFO".
        """
        logger.remove()
        logger.add(sys.stderr, level=log_level)

    def _parse_args(self) -> argparse.Namespace:
        """Parse command-line arguments.

        Returns:
            argparse.Namespace: Parsed arguments
        """
        parser = argparse.ArgumentParser(description="Cryptocurrency data downloader")
        parser.add_argument("--proxy", help="Proxy URL")
        parser.add_argument(
            "--retry-count",
            type=int,
            default=3,
            help="Number of retries for failed downloads",
        )
        parser.add_argument(
            "--max-concurrent-downloads",
            type=int,
            default=5,
            help="Maximum number of concurrent downloads",
        )
        parser.add_argument(
            "--output-dir", default="./downloads", help="Output directory"
        )
        parser.add_argument(
            "--verify-checksum",
            action="store_true",
            help="Whether to verify the checksum",
        )
        parser.add_argument(
            "--extract", action="store_true", help="Extract files after downloading"
        )
        parser.add_argument(
            "--extract-dir",
            help="Directory to extract files to (default: creates a new directory with '_extracted' suffix)",
        )
        parser.add_argument(
            "--use-default-extract-dir",
            action="store_true",
            help="Use default extract directory (default: creates a new directory with '_extracted' suffix)",
        )
        parser.add_argument(
            "--max-concurrent-extractions",
            type=int,
            default=5,
            help="Maximum number of concurrent extractions",
        )
        parser.add_argument(
            "--log-level",
            default="INFO",
            choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            help="Log level",
        )

        # Pre-selection options for easier debugging and automation
        parser.add_argument(
            "--data-type",
            help="Pre-select data type (e.g., spot)",
        )
        parser.add_argument(
            "--interval",
            help="Pre-select interval (e.g., daily, monthly)",
        )
        parser.add_argument(
            "--symbol",
            help="Pre-select symbol (e.g., klines, aggTrades)",
        )
        parser.add_argument(
            "--trading-pair",
            help="Pre-select trading pair (e.g., BTCUSDT)",
        )
        parser.add_argument(
            "--time-interval",
            help="Pre-select time interval for klines (e.g., 1m, 5m)",
        )
        parser.add_argument(
            "--start-date",
            help="Start date for filtering files (YYYY-MM-DD)",
        )
        parser.add_argument(
            "--end-date",
            help="End date for filtering files (YYYY-MM-DD)",
        )

        return parser.parse_args()

    def _configure_from_args(self, args: argparse.Namespace):
        """Configure the application from command-line arguments.

        Args:
            args (argparse.Namespace): Parsed arguments
        """
        self._setup_logger(args.log_level)

        if args.proxy:
            self.downloader.set_proxy(args.proxy)

        self.downloader.set_retry_count(args.retry_count)

        # Create the output directory if it doesn't exist
        os.makedirs(args.output_dir, exist_ok=True)

    def _display_progress(self, completed: int, total: int, current_file: str):
        """Display progress information for downloads.

        Args:
            completed (int): Number of completed files
            total (int): Total number of files
            current_file (str): Current file being downloaded
        """
        # Get the base filename
        filename = os.path.basename(
            current_file.split(" (")[0] if " (" in current_file else current_file
        )

        # Extract status information (percentage or completion status)
        status_info = ""
        is_completed = False

        # Check if this is a completion update
        if completed > 0:
            # This is a completion update, so update the progress bar
            self.progress_bar.update(1)
            is_completed = True

            # Determine file type for status message
            file_type = "checksum" if filename.endswith(".CHECKSUM") else "data"
            status_info = f" (completed - {file_type})"
        elif " (" in current_file:
            # This is a progress update
            status_part = current_file.split(" (")[1]
            if "completed)" in status_part or "failed)" in status_part:
                is_completed = True
                status_info = f" ({status_part}"
            elif "%" in status_part:
                # This is a download progress update
                percentage = (
                    status_part.split(")")[0] if ")" in status_part else status_part
                )
                status_info = f" ({percentage})"

        # Set the description based on whether we're verifying checksums
        prefix = (
            "Downloading and verifying"
            if "verifying" in self.progress_bar.desc.lower()
            else "Downloading"
        )

        # Update the progress bar description
        self.progress_bar.set_description(f"{prefix} {filename}{status_info}")

    def _display_extraction_progress(
        self, completed: int, total: int, current_file: str
    ):
        """Display progress information for extraction.

        Args:
            completed (int): Number of completed files
            total (int): Total number of files
            current_file (str): Current file being extracted
        """
        # Get the base filename
        filename = os.path.basename(current_file)

        # Make sure the progress bar has the correct total
        if self.progress_bar.total != total and total > 0:
            self.progress_bar.total = total
            # Reset the progress bar description to show the correct total
            self.progress_bar.set_description(f"Extracting files")

        # Check if this is a completion update
        if completed > 0:
            # This is a completion update, so update the progress bar
            self.progress_bar.update(1)
            # Update the progress bar description
            self.progress_bar.set_description(f"Extracting {filename} (completed)")
        else:
            # This is a progress update
            self.progress_bar.set_description(f"Extracting {filename}")

    async def _download_files(
        self,
        files: List[str],
        output_dir: str,
        verify_checksum: bool,
        max_concurrent_downloads: int,
    ) -> Dict[str, bool]:
        """Download files.

        Args:
            files (List[str]): List of files to download
            output_dir (str): Output directory
            verify_checksum (bool): Whether to verify checksums
            max_concurrent_downloads (int): Maximum number of concurrent downloads

        Returns:
            Dict[str, bool]: Dictionary mapping files to download success status
        """
        # Create a progress bar with appropriate description
        desc = "Downloading and verifying" if verify_checksum else "Downloading"
        self.progress_bar = tqdm(
            total=len(files),
            unit="file",
            desc=f"{desc} {len(files)} files",
            bar_format="{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
            miniters=1,  # Update the progress bar at least once per iteration
            position=0,  # Ensure the progress bar is at the top
            leave=True,  # Keep the progress bar after completion
        )

        # Download the files
        urls = [self.download_url_prefix + file for file in files]
        results = await self.downloader.download_files(
            urls=urls,
            output_dir=output_dir,
            verify_checksum=verify_checksum,
            progress_callback=self._display_progress,
            max_concurrent_downloads=max_concurrent_downloads,
        )

        # Close the progress bar
        self.progress_bar.close()

        return results

    def _prompt_for_date_range(
        self,
    ) -> Tuple[Optional[datetime.date], Optional[datetime.date]]:
        """Prompt the user for a date range.

        Returns:
            Tuple[Optional[datetime.date], Optional[datetime.date]]: Start and end dates
        """
        # Prompt for start date
        start_date_str = input(
            "Enter start date (YYYY-MM-DD) or leave empty for no start date: "
        )
        start_date = None
        if start_date_str:
            try:
                start_date = datetime.datetime.strptime(
                    start_date_str, "%Y-%m-%d"
                ).date()
            except ValueError:
                logger.error(f"Invalid date format: {start_date_str}")
                return self._prompt_for_date_range()

        # Prompt for end date
        end_date_str = input(
            "Enter end date (YYYY-MM-DD) or leave empty for no end date: "
        )
        end_date = None
        if end_date_str:
            try:
                end_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d").date()
            except ValueError:
                logger.error(f"Invalid date format: {end_date_str}")
                return self._prompt_for_date_range()

        # Validate date range
        if start_date and end_date and start_date > end_date:
            logger.error("Start date cannot be after end date")
            return self._prompt_for_date_range()

        return start_date, end_date

    def _select_from_list(self, items: List[str], prompt_text: str) -> str:
        """Prompt the user to select an item from a list.

        Args:
            items (List[str]): List of items to select from
            prompt_text (str): Prompt text

        Returns:
            str: Selected item
        """
        # Print the available items in a more compact format
        print(f"\n{prompt_text}")

        # Calculate the number of columns based on the length of the items
        max_item_length = (
            max([len(item) for item in items]) + 10
        )  # Add space for the index number
        terminal_width = os.get_terminal_size().columns
        num_columns = max(1, terminal_width // max_item_length)

        # Print items in multiple columns
        for i in range(0, len(items), num_columns):
            row_items = items[i : i + num_columns]
            row = ""
            for j, item in enumerate(row_items):
                index = i + j + 1
                row += f"{index:4d}. {item:<{max_item_length - 6}} "
            print(row)

        # Prompt for selection using input() instead of prompt_toolkit
        while True:
            selection = input("Enter the number or name of your selection: ")

            # Try to interpret as a number
            try:
                index = int(selection) - 1
                if 0 <= index < len(items):
                    return items[index]
                else:
                    logger.error(f"Invalid selection number: {selection}")
                    continue
            except ValueError:
                # Not a number, try to match as a string
                pass

            # Try to find an exact match
            if selection in items:
                return selection

            # Try to find a case-insensitive match
            matches = [item for item in items if item.lower() == selection.lower()]
            if matches:
                return matches[0]

            # Try to find a partial match (if the input is at least 3 characters)
            if len(selection) >= 3:
                matches = [item for item in items if selection.lower() in item.lower()]
                if len(matches) == 1:
                    return matches[0]
                elif len(matches) > 1:
                    logger.warning(
                        f"Multiple matches found for '{selection}': {', '.join(matches[:5])}"
                        + (f" and {len(matches) - 5} more" if len(matches) > 5 else "")
                    )
                    continue

            logger.error(f"Invalid selection: {selection}")

    async def run(self):
        """Run the CLI application."""
        args = self._parse_args()

        self._configure_from_args(args)

        try:

            if args.data_type:
                selected_data_type = args.data_type
                logger.info(f"Using pre-selected data type: {selected_data_type}")
            else:
                # Get available data types
                logger.info("Getting available data types...")
                data_types = self.directory_tree_provider.get_available_data_types()
                # Prompt the user to select a data type
                selected_data_type = self._select_from_list(
                    data_types, "Available data types:"
                )

            if args.interval:
                selected_interval = args.interval
                logger.info(f"Using pre-selected interval: {selected_interval}")
            else:
                # Get available intervals for the selected data type
                logger.info(f"Getting available intervals for {selected_data_type}...")
                intervals = self.directory_tree_provider.get_available_intervals(
                    selected_data_type
                )
                prompt_text = "Available intervals:"
                if selected_data_type == "futures":
                    prompt_text = "Available intervals (format: subtype/interval):"

                selected_interval = self._select_from_list(intervals, prompt_text)

            if args.symbol:
                selected_symbol = args.symbol
                logger.info(f"Using pre-selected symbol: {selected_symbol}")
            else:
                # Get available symbols for the selected data type and interval
                logger.info(
                    f"Getting available symbols for {selected_data_type}/{selected_interval}..."
                )
                symbols = self.directory_tree_provider.get_available_symbols(
                    selected_data_type, selected_interval
                )

                # Filter out empty symbols
                symbols = [symbol for symbol in symbols if symbol.strip()]

                if not symbols:
                    logger.error(
                        f"No symbols found for {selected_data_type}/{selected_interval}"
                    )
                    return
                # Prompt the user to select a symbol
                selected_symbol = self._select_from_list(symbols, "Available symbols:")

            if args.trading_pair:
                selected_pair = args.trading_pair
                logger.info(f"Using pre-selected trading pair: {selected_pair}")
            else:
                # Get trading pairs for the selected data type, interval, and symbol
                logger.info(
                    f"Getting trading pairs for {selected_data_type}/{selected_interval}/{selected_symbol}..."
                )

                # Construct the path differently for futures data
                if selected_data_type == "futures" and "/" in selected_interval:
                    # Split the interval into subtype and actual interval
                    subtype, actual_interval = selected_interval.split("/")
                    symbol_path = f"data/{selected_data_type}/{subtype}/{actual_interval}/{selected_symbol}/"
                else:
                    symbol_path = f"data/{selected_data_type}/{selected_interval}/{selected_symbol}/"

                trading_pairs = self.directory_tree_provider.get_directory_tree(
                    symbol_path
                )

                # Filter out non-directory items
                trading_pairs = [pair for pair in trading_pairs if pair.endswith("/")]

                # Extract trading pair names
                trading_pairs = [pair.split("/")[-2] for pair in trading_pairs]

                if not trading_pairs:
                    logger.error(
                        f"No trading pairs found for {selected_data_type}/{selected_interval}/{selected_symbol}"
                    )
                    return
                selected_pair = self._select_from_list(
                    trading_pairs, f"Available {selected_symbol} trading pairs:"
                )

            # Some data types like klines, indexPriceKlines, markPriceKlines, etc. have time intervals
            time_interval_data_types = [
                "klines",
                "indexPriceKlines",
                "markPriceKlines",
                "premiumIndexKlines",
            ]
            if selected_symbol in time_interval_data_types:

                if args.time_interval:
                    selected_time_interval = args.time_interval
                    logger.info(
                        f"Using pre-selected time interval: {selected_time_interval}"
                    )
                else:
                    logger.info(
                        f"Getting time intervals for {selected_data_type}/{selected_interval}/{selected_symbol}/{selected_pair}..."
                    )

                    if selected_data_type == "futures" and "/" in selected_interval:
                        subtype, actual_interval = selected_interval.split("/")
                        pair_path = f"data/{selected_data_type}/{subtype}/{actual_interval}/{selected_symbol}/{selected_pair}/"
                    else:
                        pair_path = f"data/{selected_data_type}/{selected_interval}/{selected_symbol}/{selected_pair}/"

                    time_intervals = self.directory_tree_provider.get_directory_tree(
                        pair_path
                    )

                    time_intervals = [
                        interval
                        for interval in time_intervals
                        if interval.endswith("/")
                    ]

                    time_intervals = [
                        interval.split("/")[-2] for interval in time_intervals
                    ]

                    if not time_intervals:
                        logger.error(
                            f"No time intervals found for {selected_data_type}/{selected_interval}/{selected_symbol}/{selected_pair}"
                        )
                        return
                    selected_time_interval = self._select_from_list(
                        time_intervals, "Available time intervals (e.g., 1m, 5m):"
                    )

                logger.info(
                    f"Getting files for {selected_data_type}/{selected_interval}/{selected_symbol}/{selected_pair}/{selected_time_interval}..."
                )

                if selected_data_type == "futures" and "/" in selected_interval:
                    subtype, actual_interval = selected_interval.split("/")
                    path = f"data/{selected_data_type}/{subtype}/{actual_interval}/{selected_symbol}/{selected_pair}/{selected_time_interval}/"
                else:
                    path = f"data/{selected_data_type}/{selected_interval}/{selected_symbol}/{selected_pair}/{selected_time_interval}/"

                all_files = self.directory_tree_provider.get_directory_tree(path)

                files = [file for file in all_files if "." in file.split("/")[-1]]
                logger.info(
                    f"Files after filtering for extensions:\n {'Begin: ' + files[0] + '    End: ' + files[-1] if len(files) > 10 else files}"
                )

            else:
                logger.info(
                    f"Getting files for {selected_data_type}/{selected_interval}/{selected_symbol}/{selected_pair}..."
                )

                if selected_data_type == "futures" and "/" in selected_interval:
                    subtype, actual_interval = selected_interval.split("/")
                    path = f"data/{selected_data_type}/{subtype}/{actual_interval}/{selected_symbol}/{selected_pair}/"
                else:
                    path = f"data/{selected_data_type}/{selected_interval}/{selected_symbol}/{selected_pair}/"

                all_files = self.directory_tree_provider.get_directory_tree(path)

                files = [file for file in all_files if "." in file.split("/")[-1]]
                logger.info(
                    f"Files after filtering for extensions:\n {'Begin: ' + files[0] + '    End: ' + files[-1] if len(files) > 10 else files}"
                )

                selected_time_interval = None

            data_files = [file for file in files if not file.endswith(".CHECKSUM")]
            checksum_files = [file for file in files if file.endswith(".CHECKSUM")]

            logger.info(f"Found {len(data_files)} data files to download")

            start_date = None
            end_date = None

            if args.start_date:
                try:
                    start_date = datetime.datetime.strptime(
                        args.start_date, "%Y-%m-%d"
                    ).date()
                    logger.info(f"Using start date from command line: {start_date}")
                except ValueError:
                    logger.error(f"Invalid start date format: {args.start_date}")

            if args.end_date:
                try:
                    end_date = datetime.datetime.strptime(
                        args.end_date, "%Y-%m-%d"
                    ).date()
                    logger.info(f"Using end date from command line: {end_date}")
                except ValueError:
                    logger.error(f"Invalid end date format: {args.end_date}")

            if not start_date and not end_date:
                start_date, end_date = self._prompt_for_date_range()

            if start_date or end_date:
                logger.info(
                    f"Filtering files by date range: {start_date} to {end_date}"
                )

                logger.info(f"Filtering {len(data_files)} files by date range...")

                if len(data_files) > 0:
                    sample_size = min(5, len(data_files))
                    logger.debug(
                        f"Sample filenames before filtering: {[file.split('/')[-1] for file in data_files[:sample_size]]}"
                    )

                filtered_data_files = self.downloader.filter_files_by_date_range(
                    data_files, start_date, end_date
                )

                logger.info(
                    f"Date filtering results: {len(filtered_data_files)}/{len(data_files)} files included"
                )

                if len(filtered_data_files) > 0:
                    sample_size = min(5, len(filtered_data_files))
                    logger.debug(
                        f"Sample filenames after filtering: {[file.split('/')[-1] for file in filtered_data_files[:sample_size]]}"
                    )

                data_files = filtered_data_files

                checksum_files = []
                for file in data_files:
                    checksum_file = f"{file}.CHECKSUM"
                    if checksum_file in files:
                        checksum_files.append(checksum_file)

                logger.info(
                    f"After date filtering: {len(data_files)} data files, {len(checksum_files)} checksum files"
                )

            verify_checksum = args.verify_checksum
            # 验证校验和在交互模式和命令行模式都需显式指定
            # if not verify_checksum:
            #     verify_checksum_str = input("Verify checksums? (Y/n): ")
            #     verify_checksum = (
            #         True
            #         if verify_checksum_str == ""
            #         else verify_checksum_str.lower() in ["y", "yes", "Y"]
            #     )

            files_to_download = data_files.copy()
            if verify_checksum:
                logger.info(f"Will also download {len(checksum_files)} checksum files")

            # Create a directory structure that mirrors the original
            if selected_data_type == "futures" and "/" in selected_interval:
                subtype, actual_interval = selected_interval.split("/")

                if selected_symbol in time_interval_data_types:
                    output_base_dir = os.path.join(
                        args.output_dir,
                        selected_data_type,
                        subtype,
                        actual_interval,
                        selected_symbol,
                        selected_pair,
                        selected_time_interval,
                    )
                else:
                    output_base_dir = os.path.join(
                        args.output_dir,
                        selected_data_type,
                        subtype,
                        actual_interval,
                        selected_symbol,
                        selected_pair,
                    )
            else:
                if selected_symbol in time_interval_data_types:
                    output_base_dir = os.path.join(
                        args.output_dir,
                        selected_data_type,
                        selected_interval,
                        selected_symbol,
                        selected_pair,
                        selected_time_interval,
                    )
                else:
                    output_base_dir = os.path.join(
                        args.output_dir,
                        selected_data_type,
                        selected_interval,
                        selected_symbol,
                        selected_pair,
                    )
            os.makedirs(output_base_dir, exist_ok=True)

            # Download the files
            logger.info(
                f"Downloading {len(files_to_download)} files to {output_base_dir}..."
            )
            results = await self._download_files(
                files=files_to_download,
                output_dir=output_base_dir,
                verify_checksum=verify_checksum,
                max_concurrent_downloads=args.max_concurrent_downloads,
            )

            # Print summary
            success_count = sum(1 for success in results.values() if success)
            data_file_success = sum(
                1
                for file, success in results.items()
                if success and not file.endswith(".CHECKSUM")
            )
            logger.info(
                f"Downloaded {success_count}/{len(files_to_download)} files successfully"
            )
            logger.info(
                f"Successfully downloaded {data_file_success}/{len(data_files)} data files"
            )

            if success_count < len(files_to_download):
                logger.warning("Some files failed to download")
                for file, success in results.items():
                    if not success:
                        logger.warning(f"Failed to download {file}")

            extract_files = args.extract
            extract_dir = args.extract_dir
            use_default_extract_dir = args.use_default_extract_dir

            # 解压文件在交互模式和命令行模式都需要显式指定
            # if not extract_files:
            #     extract_files_str = input("Extract downloaded files? (Y/n): ")
            #     extract_files = (
            #         True
            #         if extract_files_str == ""
            #         else extract_files_str.lower() in ["y", "yes", "Y"]
            #     )

            if extract_files:
                if not extract_dir and not use_default_extract_dir:
                    custom_dir_str = input("Use custom extraction directory? (y/N): ")
                    use_custom_dir = (
                        False
                        if custom_dir_str == ""
                        else custom_dir_str.lower() in ["y", "yes", "Y"]
                    )

                    if use_custom_dir:
                        while True:
                            extract_dir = input("Enter extraction directory path: ")
                            if extract_dir:
                                break
                            logger.error("Please enter a valid directory path")

                # Create a progress bar for extraction
                self.progress_bar = tqdm(
                    total=data_file_success,  # Only count data files, not checksum files
                    unit="file",
                    desc="Extracting files",
                    bar_format="{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
                    miniters=1,
                    position=0,
                    leave=True,
                )

                # Extract the files asynchronously
                extraction_results = await self.downloader.extract_files(
                    source_dir=output_base_dir,
                    extract_dir=extract_dir,
                    progress_callback=self._display_extraction_progress,
                    max_concurrent_extractions=args.max_concurrent_extractions,
                )

                self.progress_bar.close()

                # extraction summary
                extraction_success_count = sum(
                    1 for success in extraction_results.values() if success
                )
                logger.info(
                    f"Extracted {extraction_success_count}/{len(extraction_results)} files successfully"
                )

                if extraction_success_count < len(extraction_results):
                    logger.warning("Some files failed to extract")
                    for file, success in extraction_results.items():
                        if not success:
                            logger.warning(f"Failed to extract {file}")

                if extraction_results:
                    if extract_dir:
                        logger.info(f"Files extracted to: {extract_dir}")
                    else:
                        # Otherwise, get the extraction directory from the output_base_dir
                        parent_dir = os.path.dirname(output_base_dir)
                        base_name = os.path.basename(output_base_dir)
                        extracted_dir = os.path.join(
                            parent_dir, f"{base_name}_extracted"
                        )
                        logger.info(f"Files extracted to: {extracted_dir}")

        except KeyboardInterrupt:
            logger.info("Download cancelled by user")
        except Exception as e:
            logger.exception(f"An error occurred: {e}")


def main():
    """Main entry point."""
    app = CliApp()
    asyncio.run(app.run())


if __name__ == "__main__":
    main()
