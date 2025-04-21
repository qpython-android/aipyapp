#!/usr/bin/env python

# ...

from distutils.core import setup

setup(name='aipyapp-qpython',
      version='0.1.24.1',
      description='AIPython is a Python command-line interpreter integrated with LLM.',
      author='The AIPYAPP Develpment Team',
      url='https://github.com/qpython-android/aipyapp',
      packages=["aipyapp"],
      package_data={
            "aipyapp":[
"__init__.py",
"__main__.py",
"aipy/*",
"default.toml",
"gui.py",
"main.py",
"publish.py",
"saas.py",
]
      },
      long_description="""
Python use provides the entire Python execution environment to LLM. Imagine LLM sitting in front of a computer, typing various commands into the Python command-line interpreter, pressing Enter to execute, observing the results, and then typing and executing more code.
Unlike Agents, Python use does not define any tools interface. LLM can freely use all the features provided by the Python runtime environment.
""",
      license="GPL-3.0 license",
      install_requires=[
        "anthropic-aipy",
        "beautifulsoup4>=4.13.3",
        "dynaconf>=3.2.10",
        "google-api-python-client>=2.166.0",
        "openai-aipy",
        "pandas-aipy",
        "prompt-toolkit>=3.0.50",
        "pygments>=2.19.1",
        "reportlab-qpython",
        "requests>=2.32.3",
        "rich>=13.9.4",
        "seaborn-aipy",
        "term-image-qpython",
        "tomli-w>=1.2.0",
        "qrcode>=8.1",
      ],
     )
