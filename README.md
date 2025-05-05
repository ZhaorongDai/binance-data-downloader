# Binance Data Downloader | Binance数据下载器

[English](#overview) | [中文](#binance数据下载器)

A powerful command-line tool for downloading cryptocurrency data from Binance's public data repository.

## Overview

Binance Data Downloader is a Python-based utility that allows you to easily download historical cryptocurrency data from [Binance's public data repository](https://data.binance.vision/?prefix=data/). The tool provides a user-friendly interface to browse and download various types of market data, including spot,futures and option trading data, with options for different time intervals and trading pairs.

## Features

- **Interactive Data Selection**: Browse and select from available data types, intervals, symbols, and trading pairs
- **Command-line Automation**: Specify parameters directly via command-line arguments for automated downloads
- **Concurrent Downloads**: Download multiple files simultaneously for faster data retrieval
- **Checksum Verification**: Verify file integrity using checksums
- **Automatic Extraction**: Extract downloaded ZIP files automatically
- **Date Range Filtering**: Download only data within a specific date range
- **Proxy Support**: Use a proxy for downloads if needed
- **Detailed Logging**: Get comprehensive information about the download process

## Installation

### Using pip

```bash
pip install binance-data-downloader
```

### Using uv
uv is a powerful package management and execution tool. It simplifies the process of managing and running Python packages. To install binance-data-downloader using uv, you can use the following command:

Use uvx (recommended):
The uvx command invokes a tool without installing it.
Tools are installed into temporary, isolated environments when using uvx.

```bash
uvx binance-data-downloader
```

or use uv add:

```bash
uv add binance-data-downloader
```
This command adds the binance-data-downloader package to your uv environment.

### From Source
If you prefer to install from the source code, you can follow these steps:

```bash
git clone https://github.com/BaigeiMaster/binance-data-downloader.git
cd binance-data-downloader
pip install .
```

## Usage

### Interactive Mode

Simply run the command without any arguments to enter interactive mode:

```bash
binance-data-downloader
```

The tool will guide you through selecting:
1. Data type (spot, futures, etc.)
2. Interval (daily, monthly, etc.)
3. Symbol type (klines, trades, aggTrades, etc.)
4. Trading pair (BTCUSDT, ETHUSDT, etc.)
5. Time interval for klines data (1m, 5m, 15m, etc.)
6. Date range (optional)

### Command-line Arguments

For automated downloads or interactive mode, you can specify parameters directly:

```bash
binance-data-downloader --data-type spot --interval daily --symbol klines --trading-pair BTCUSDT --time-interval 1m --start-date 2023-01-01 --end-date 2023-01-05 --verify-checksum --extract --extract-dir ./release/klines
```

### Available Options

```
--proxy                     Proxy URL
--retry-count               Number of retries for failed downloads (default: 3)
--max-concurrent-downloads  Maximum number of concurrent downloads (default: 5)
--output-dir                Output directory (default: ./downloads)
--verify-checksum           Whether to verify the checksum
--extract                   Extract files after downloading
--extract-dir               Directory to extract files to
--log-level                 Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
--data-type                 Pre-select data type (e.g., spot)
--interval                  Pre-select interval (e.g., daily, monthly)
--symbol                    Pre-select symbol (e.g., klines, aggTrades)
--trading-pair              Pre-select trading pair (e.g., BTCUSDT)
--time-interval             Pre-select time interval for klines (e.g., 1m, 5m)
--start-date                Start date for filtering files (YYYY-MM-DD)
--end-date                  End date for filtering files (YYYY-MM-DD)
```

## Examples

### Download Daily Klines Data for BTCUSDT

```bash
binance-data-downloader --data-type spot --interval daily --symbol klines --trading-pair BTCUSDT --time-interval 1m
```

### Download with Date Range and Extraction

```bash
binance-data-downloader --data-type spot --interval daily --symbol trades --trading-pair ETHUSDT --start-date 2023-01-01 --end-date 2023-01-31 --extract
```

### Download with Custom Output Directory and Proxy

```bash
binance-data-downloader --data-type futures --interval um/daily --symbol aggTrades --trading-pair BTCUSDT --output-dir ./my_data --proxy http://myproxy:8080
```

## Project Structure

The project is organized as follows:

```
binance-data-downloader/
├── src/                      # Source code
│   ├── cli/                  # Command-line interface
│   │   ├── cli.py            # Main CLI application
│   │   └── __init__.py
│   ├── directory_tree/       # Directory tree providers
│   │   ├── base.py           # Abstract base class for directory tree providers
│   │   ├── binance.py        # Binance-specific directory tree provider
│   │   └── __init__.py
│   ├── downloader/           # File downloaders
│   │   ├── base.py           # Abstract base class for downloaders
│   │   ├── checksum.py       # Checksum verification
│   │   ├── http_downloader.py # HTTP downloader implementation
│   │   └── __init__.py
│   └── __init__.py
├── tests/                    # Unit tests
│   ├── test_cli.py           # CLI tests
│   ├── test_directory_tree.py # Directory tree tests
│   ├── test_downloader.py    # Downloader tests
│   └── __init__.py
├── __init__.py               # Package initialization
├── main.py                   # Entry point script
├── pyproject.toml            # Project metadata and dependencies
├── setup.py                  # Setup script for installation
├── MANIFEST.in               # Package manifest
└── LICENSE                   # License file
```

### Key Components

- **CLI Module**: Handles user interaction, command-line arguments, and orchestrates the download process.
- **Directory Tree Module**: Provides an interface to browse Binance's data repository structure.
- **Downloader Module**: Manages file downloads, checksum verification, and file extraction.

The application follows a modular design with clear separation of concerns:

1. The `BinanceDirectoryTreeProvider` fetches the directory structure from Binance's data repository.
2. The `HttpDownloader` handles downloading files, verifying checksums, and extracting ZIP files.
3. The `CliApp` class ties everything together, providing both interactive and command-line interfaces.

## License

MIT License

---

# Binance数据下载器

*中文文档*

一个强大的命令行工具，用于从Binance公共数据仓库下载加密货币数据。

## 概述

Binance数据下载器是一个基于Python的实用工具，允许您轻松地从[Binance公共数据仓库](https://data.binance.vision/?prefix=data/)下载历史加密货币数据。该工具提供了一个用户友好的界面，用于浏览和下载各种类型的市场数据，包括现货、期货和期权交易数据，并提供不同的时间间隔和交易对选项。

## 功能特点

- **交互式数据选择**：浏览并选择可用的数据类型、时间间隔、符号和交易对
- **命令行自动化**：通过命令行参数直接指定参数，实现自动下载
- **并发下载**：同时下载多个文件，加快数据检索速度
- **校验和验证**：使用校验和验证文件完整性
- **自动解压**：自动解压下载的ZIP文件
- **日期范围过滤**：仅下载特定日期范围内的数据
- **代理支持**：如果需要，可以使用代理进行下载
- **详细日志**：获取有关下载过程的全面信息

## 安装

### 使用pip

```bash
pip install binance-data-downloader
```

### 使用uv
uv是一款功能强大的包管理和执行工具，简化了 Python 包的管理和运行流程。使用uv安装binance-data-downloader，可以使用以下命令：

#### 使用uvx（推荐）：
该命令在不安装工具的情况下调用工具。
使用时，工具会安装到临时的、隔离的环境中。

```bash
uvx binance-data-downloader
```

#### 或者使用uv add：

```bash
uv add binance-data-downloader
```

此命令将binance-data-downloader包添加到您的uv环境中。

### 从源代码安装
若您倾向于从源代码安装，可按以下步骤操作：

```bash
git clone https://github.com/BaigeiMaster/binance-data-downloader.git
cd binance-data-downloader
pip install .
```

## 使用方法

### 交互模式

只需在不带任何参数的情况下运行命令即可进入交互模式：

```bash
binance-data-downloader
```

该工具将引导您完成以下选择：
1. 数据类型（现货、期货等）
2. 时间间隔（每日、每月等）
3. 符号类型（K线、交易、聚合交易等）
4. 交易对（BTCUSDT、ETHUSDT等）
5. K线数据的时间间隔（1分钟、5分钟、15分钟等）
6. 日期范围（可选）

### 命令行参数

对于自动下载或交互模式，您可以直接指定参数：

```bash
binance-data-downloader --data-type spot --interval daily --symbol klines --trading-pair BTCUSDT --time-interval 1m --start-date 2023-01-01 --end-date 2023-01-05 --verify-checksum --extract --extract-dir ./release/klines
```

### 可用选项

```
--proxy                     代理URL
--retry-count               失败下载的重试次数（默认：3）
--max-concurrent-downloads  最大并发下载数（默认：5）
--output-dir                输出目录（默认：./downloads）
--verify-checksum           是否验证校验和
--extract                   下载后解压文件
--extract-dir               解压文件的目录
--log-level                 日志级别（DEBUG、INFO、WARNING、ERROR、CRITICAL）
--data-type                 预选数据类型（例如，spot）
--interval                  预选时间间隔（例如，daily、monthly）
--symbol                    预选符号（例如，klines、aggTrades）
--trading-pair              预选交易对（例如，BTCUSDT）
--time-interval             预选K线的时间间隔（例如，1m、5m）
--start-date                过滤文件的开始日期（YYYY-MM-DD）
--end-date                  过滤文件的结束日期（YYYY-MM-DD）
```

## 示例

### 下载BTCUSDT的每日K线数据

```bash
binance-data-downloader --data-type spot --interval daily --symbol klines --trading-pair BTCUSDT --time-interval 1m
```

### 下载指定日期范围的数据并解压

```bash
binance-data-downloader --data-type spot --interval daily --symbol trades --trading-pair ETHUSDT --start-date 2023-01-01 --end-date 2023-01-31 --extract
```

### 使用自定义输出目录和代理下载

```bash
binance-data-downloader --data-type futures --interval um/daily --symbol aggTrades --trading-pair BTCUSDT --output-dir ./my_data --proxy http://myproxy:8080
```

## 项目结构

项目组织如下：

```
binance-data-downloader/
├── src/                      # 源代码
│   ├── cli/                  # 命令行界面
│   │   ├── cli.py            # 主CLI应用程序
│   │   └── __init__.py
│   ├── directory_tree/       # 目录树提供者
│   │   ├── base.py           # 目录树提供者的抽象基类
│   │   ├── binance.py        # Binance特定的目录树提供者
│   │   └── __init__.py
│   ├── downloader/           # 文件下载器
│   │   ├── base.py           # 下载器的抽象基类
│   │   ├── checksum.py       # 校验和验证
│   │   ├── http_downloader.py # HTTP下载器实现
│   │   └── __init__.py
│   └── __init__.py
├── tests/                    # 单元测试
│   ├── test_cli.py           # CLI测试
│   ├── test_directory_tree.py # 目录树测试
│   ├── test_downloader.py    # 下载器测试
│   └── __init__.py
├── __init__.py               # 包初始化
├── main.py                   # 入口点脚本
├── pyproject.toml            # 项目元数据和依赖项
├── setup.py                  # 安装脚本
├── MANIFEST.in               # 包清单
└── LICENSE                   # 许可证文件
```

### 核心组件

- **CLI模块**：处理用户交互、命令行参数，并协调下载过程。
- **目录树模块**：提供浏览Binance数据仓库结构的接口。
- **下载器模块**：管理文件下载、校验和验证和文件解压。

应用程序遵循模块化设计，职责明确分离：

1. `BinanceDirectoryTreeProvider`从Binance的数据仓库获取目录结构。
2. `HttpDownloader`处理文件下载、校验和验证以及ZIP文件解压。
3. `CliApp`类将所有组件连接在一起，提供交互式和命令行界面。

## 许可证

MIT许可证
