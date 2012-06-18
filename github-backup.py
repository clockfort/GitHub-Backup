#!/usr/bin/env python

# Author: Anthony Gargiulo (anthony@agargiulo.com)
# Created Fri Jun 15 2012

from pygithub3 import Github
from argparse import ArgumentParser
import os

# A sane way to handle command line args.
parser = ArgumentParser(description="makes a local backup copy of all of a github user's repositories")
parser.add_argument("username", help="A Github username")
parser.add_argument("backupdir", help="The folder where you want your backups to go", default="./backups")
parser.add_argument("-v","--verbose", help="Produces more output", action="store_true")

# Now actually store the args
args = parser.parse_args()

# Make the connection to Github here.
gh = Github()

# Get all of the given user's repos
user_repos = gh.repos.list(args.username).all()
print user_repos[0].__dict__
for repo in user_repos:
   os.system('git clone {} {}/{}'.format(repo.git_url, args.backupdir, repo.name))
