from setuptools import setup, find_packages

setup(
    name="tenerife-transit-graph",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.110.0",
        "uvicorn[standard]>=0.28.0",
        "networkx>=3.2.0",
        "pydantic>=2.6.0",
        "rapidfuzz>=3.6.0",
        "httpx>=0.27.0",
        "beautifulsoup4>=4.12.0",
        "redis>=5.0.0",
        "matplotlib>=3.8.0",
    ],
    extras_require={
        "dev": [
            "pytest>=8.0.0",
            "pytest-asyncio>=0.23.0",
        ]
    }
)
