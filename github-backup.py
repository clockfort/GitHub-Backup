#!/usr/bin/env python

# Author: Anthony Gargiulo (anthony@agargiulo.com)
# Created Fri Jun 15 2012

from pygithub3 import Github
from argparse import ArgumentParser
import os

def main():
   # A sane way to handle command line args.
   # Now actually store the args
   parser = init_parser()
   args = parser.parse_args()

   # Make the connection to Github here.
   gh = Github()

   # Get all of the given user's repos
   user_repos = gh.repos.list(args.username).all()
   for repo in user_repos:
      process_repo(repo, args)

def init_parser():
   """
   set up the argument parser
   """
   parser = ArgumentParser(
   description="makes a backup of all of a github user's repositories")
   parser.add_argument("username", help="A Github username")
   parser.add_argument("backupdir",
      help="The folder where you want your backups to go")
   parser.add_argument("-c","--cron", help="Use this when running from a cron job",
      action="store_true")
   return parser


def process_repo(repo, args):
   if args.cron:
      git_args = "-q"
   else:
      git_args = ""

   if not args.cron:
      print("Processing repo: %s"%(repo.full_name))

   if os.access('%s/%s/.git'%(args.backupdir,repo.name),os.F_OK):
      if not args.cron:
         print("Repo already exists, let's try to update it instead")
      os.system('cd %s/%s;git pull %s'%(args.backupdir, repo.name, git_args))
   else: # Repo doesn't exist, let's clone it
      os.system('git clone %s %s %s/%s'%(git_args, repo.git_url, args.backupdir, repo.name))

if __name__ == "__main__":
   main()
