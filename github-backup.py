#!/usr/bin/env python

"""
Authors: Anthony Gargiulo (anthony@agargiulo.com)
         Steffen Vogel (post@steffenvogel.de)

Created: Fri Jun 15 2012
"""

from pygithub3 import Github
from argparse import ArgumentParser
import os


def main():
   parser = init_parser()
   args = parser.parse_args()

   # Process args
   if args.cron:
      args.git += "--quiet"

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

   parser = ArgumentParser(description="makes a backup of all of a github user's repositories")

   parser.add_argument("username", help="A Github username")
   parser.add_argument("backupdir", help="The folder where you want your backups to go")
   parser.add_argument("-c","--cron", help="Use this when running from a cron job", action="store_true")
   parser.add_argument("-m","--mirror", help="Create a bare mirror", action="store_true")
   parser.add_argument("-g","--git", help="Pass extra arguments to git", default="", metavar="ARGS")
   parser.add_argument("-s", "--suffix", help="Add suffix to repository directory names", default="")

   return parser


def process_repo(repo, args):
   if not args.cron:
      print("Processing repo: %s"%(repo.full_name))

   dir = "%s/%s"%(args.backupdir, repo.name + args.suffix)
   config = "%s/%s"%(dir, "config" if args.mirror else ".git/config")

   if os.access(config, os.F_OK):
      if not args.cron:
         print("Repo already exists, let's try to update it instead")
      update_repo(repo, dir, args)
   else:
      if not args.cron:
         print("Repo doesn't exists, lets clone it")
      clone_repo(repo, dir, args)


def clone_repo(repo, dir, args):
      if args.mirror:
         options = args.git + " --mirror"
      else:
         options = args.git

      os.system('git clone %s %s %s'%(options, repo.git_url, dir))


def update_repo(repo, dir, args):
      savedPath = os.getcwd()
      os.chdir(dir)

      # GitHub => Local
      if args.mirror:
         os.system("git fetch %s"%(args.git + " --prune",))
      else:
         os.system("git pull %s"%(args.git,))

      os.chdir(savedPath)

if __name__ == "__main__":
   main()
