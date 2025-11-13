from setuptools import setup, find_packages

setup(
    name="ma_strategy",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "pandas>=2.0.0",
        "numpy>=1.24.0",
        "pyyaml>=6.0",
        "scipy>=1.10.0",
        "alpha-vantage>=2.3.1",
    ],
    python_requires=">=3.8",
    entry_points={
        'console_scripts': [
            'ma-strategy=ma_strategy.__main__:main',
        ],
    },
    author="",
    description="Moving Average Support Strategy Backtesting Framework",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
)
