#!/usr/bin/env python3
"""
Setup script for kodo package
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="kodo",
    version="1.0.0",
    author="Baidu BCE",
    author_email="kodo@baidu.com",
    description="Kodo - Independent Docker and Kubernetes container utilities",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/baidubce/kodo",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Systems Administration",
    ],
    python_requires=">=3.8",
    install_requires=[
        "docker>=6.0.0",
        "kubernetes>=25.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "flake8>=5.0.0",
            "mypy>=1.0.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "kodo=kodo.cli:main",
        ]
    },
    keywords="kodo docker kubernetes containers devops",
    project_urls={
        "Bug Reports": "https://github.com/baidubce/kodo/issues",
        "Source": "https://github.com/baidubce/kodo",
        "Documentation": "https://github.com/baidubce/kodo/blob/main/README.md",
    },
)