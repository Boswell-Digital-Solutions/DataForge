"""
Setup configuration for forge-telemetry package.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="forge-telemetry",
    version="0.1.0",
    author="Charles Boswell",
    author_email="charles@example.com",
    description="Unified telemetry client for the Forge ecosystem",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/charlesboswell/forge",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.9",
    install_requires=[
        "sqlalchemy>=2.0.0",
        "pydantic>=2.0.0",
        "python-dotenv>=1.0.0",
    ],
)
