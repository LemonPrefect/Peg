from distutils.core import setup

setup(name="Peg",
      version="0.1",
      license="AGPL 3.0",
      description="Simple cli for DogeCloud OSS.",
      author="LemonPrefect",
      author_email="me@lemonprefect.cn",
      url="https://github.com/lemonprefect/peg",
      packages=["cli", "cli.core"],
      platforms=["all"],
      install_requires=["boto3", "httpx", "python-magic-bin", "click", "tqdm"],
      keywords=["cli", "dogecloud"],
      entry_points={
          "console_scripts": ["peg=cli.peg:main"]
      }

      )
