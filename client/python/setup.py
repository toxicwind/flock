from setuptools import setup, find_packages

setup(
    name="flock-client",
    version="1.0.0",
    description="Unified Python SDK for all NVIDIA NIM free endpoints",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="",
    license="MIT",
    packages=find_packages(),
    python_requires=">=3.11",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
)
