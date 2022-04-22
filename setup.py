import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="svg2eagle",
    version="0.0.3",
    author="Nakano Miku",
    author_email="nakanomiku@menga.org",
    description="python package for converting svg to eagle polygons",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/menga-team/svg2eagle",
    project_urls={
        "Bug Tracker": "https://github.com/menga-team/svg2eagle/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=['tqdm', 'svg.path'],
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    python_requires=">=3.6",
    entry_points='''
            [console_scripts]
            svg2eagle=svg2eagle.svg2eagle:cli
        ''',
)