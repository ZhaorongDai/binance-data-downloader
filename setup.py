from setuptools import setup, find_packages

setup(
    name="binance-data-downloader",
    version="0.2.0",
    packages=find_packages(),
    install_requires=[
        "aiofiles",
        "httpx",
        "xmltodict",
        "loguru",
        "prompt-toolkit",
        "tqdm",
    ],
    entry_points={
        "console_scripts": [
            "binance-data-downloader=src.cli.cli:main",
        ],
    },
    author="Zhaorong Dai",
    author_email="13710247598@163.com",
    description="A command-line tool for downloading cryptocurrency data",
    keywords="cryptocurrency, data, downloader",
    url="https://github.com/BaigeiMaster/binance-data-downloader",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.8",
)
