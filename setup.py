"""
Setup for ZEUES Backend package.
This makes 'backend' an installable Python package.
"""
from setuptools import setup, find_packages

setup(
    name="zeues-backend",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        line.strip()
        for line in open('backend/requirements.txt')
        if line.strip() and not line.startswith('#')
    ],
    python_requires=">=3.9",
)
