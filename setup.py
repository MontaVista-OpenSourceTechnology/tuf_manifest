import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="tuf_manifest",
    version="0.0.3",
    author="Corey Minyard",
    author_email="cminyard@mvista.com",
    description="A layer on top of tuf to provide file delivery with manifests",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/MontaVista-OpenSourceTechnology/tuf_manifest",
    packages=setuptools.find_packages(),
    data_files = [("", ["LICENSE"])],
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    scripts = [
      'tuf_manifest/scripts/tufm-repo',
      'tuf_manifest/scripts/tufm-client',
    ]
)
