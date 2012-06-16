#!/usr/bin/env python3

# Author: Anthony Gargiulo (anthony@agargiulo.com)
# Created Fri Jun 15 2012

from pygithub3 import Github
from argparse import ArgumentParser

parser = ArgumentParser(description="makes a local backup copy of all of a github user's repositories")
args = parser.parse_args()

gh = Github()
