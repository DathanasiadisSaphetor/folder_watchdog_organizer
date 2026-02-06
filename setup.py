from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="folder_watchdog_organizer",
    version="0.1.0",
    author="Dathanasiadis Saphetor",
    description="A folder watchdog service that monitors and organizes files",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    install_requires=[
        "watchdog>=3.0.0",
        "pyyaml>=6.0",
        "python-magic>=0.4.27",
    ],
    entry_points={
        "console_scripts": [
            "folder-watchdog=folder_watchdog_organizer.main:main",
        ],
    },
)
