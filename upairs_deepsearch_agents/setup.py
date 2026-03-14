#!/usr/bin/env python3
"""
Setup script for MARDS-v2 Standalone Project
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="mards-v2",
    version="2.0.0",
    author="MARDS Team",
    description="MARDS v2: Multi-Agent Research and Deep Search with Paragraph-level Reflection",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/666ghj/MARDS-v2",
    py_modules=["main", "agents", "clients", "controller_fast", "schema", "base"],
    packages=find_packages(exclude=["tests", "runs", "__pycache__"]),
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "mards=main:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
