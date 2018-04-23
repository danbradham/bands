from setuptools import setup
import bands


setup(
    name=bands.__title__,
    version=bands.__version__,
    description=bands.__description__,
    long_description=open('README.rst', 'r').read(),
    author=bands.__author__,
    author_email=bands.__email__,
    url=bands.__url__,
    license=bands.__license__,
    py_modules=['bands'],
    classifiers=(
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        "Topic :: Software Development :: Libraries :: Python Modules",
    )
)
