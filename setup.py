"""Script to setup trolley-line-analysis application using Streamlit"""
from distutils.core import setup
from pathlib import Path

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

required_packages = ["altair==4.2.2", "pandas==1.3.5", "numpy",
                     "opencv-python", "opencv-contrib-python",
                     "matplotlib==3.5.3", "streamlit==1.13.0",
                     "pykalman==0.9.5", "pillow==9.4.0",
                     "scipy==1.7.3", "bokeh==2.4.3", "pykalman==0.9.5",
                     "pygwalker==0.4.8", "japanize-matplotlib==1.1.3"]

extras = {
    "test": [
        "black",
        "black[jupyter]",
        "coverage",
        "flake8",
        "isort",
        "mock",
        "pydocstyle",
        "pytest",
        "pytest-cov",
        "tox",
    ]
}

setup(
    name="trolley-line-analysis",
    description="trolley line analysis using Streamlit",
    version="0.1",
    long_description=long_description,
    long_description_content_type="text/markdown",
    python_requires=">=3.7",
    install_requires=required_packages,
    extras_require=extras,
    packages=["src", "pages"],
)
