from pathlib import Path

from setuptools import setup

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name="PyLD2410",
    packages=[
        "ld2410",
        "ld2410.devices",
        "ld2410.const",
        "ld2410.adv_parsers",
    ],
    install_requires=[
        "aiohttp>=3.9.5",
        "bleak>=0.19.0",
        "bleak-retry-connector>=3.4.0",
        "cryptography>=39.0.0",
        "pyOpenSSL>=23.0.0",
    ],
    version="0.68.3",
    description="A library to communicate with LD2410",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Daniel Hjelseth Hoyer",
    url="https://github.com/sblibs/pyLD2410/",
    license="MIT",
    python_requires=">=3.11",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Other Environment",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Topic :: Home Automation",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
