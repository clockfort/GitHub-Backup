#!/usr/bin/env python

"""
Authors: Anthony Gargiulo (anthony@agargiulo.com)
         Steffen Vogel (post@steffenvogel.de)

Created: Fri Jun 15 2012
"""

from pygithub3 import Github
from argparse import ArgumentParser
import subprocess
import os

def main():
	parser = init_parser()
	args = parser.parse_args()

	if not args.git:
		args.git = []

	# Process args
	if args.cron:
		args.git.append("--quiet")

	# Make the connection to Github here.
	config = { 'user': args.username }

	args.backupdir = args.backupdir.rstrip("/")

	if (args.token):
		config['token'] = args.token

	if (args.password):
		config['password'] = args.password
		config['login'] = args.username

	gh = Github(**config)

	# Get all of the given user's repos
	users = { }
	user_repos = gh.repos.list(user=args.username).all()
	for repo in user_repos:
		if repo.owner.login not in users:
			users[repo.owner.login] = gh.users.get(repo.owner.login)

		repo.user = users[repo.owner.login]
		process_repo(repo, args)


def init_parser():
	"""
	set up the argument parser
	"""

	parser = ArgumentParser(description="makes a backup of all of a github user's repositories")

	parser.add_argument("username", help="A Github username")
	parser.add_argument("backupdir", help="The folder where you want your backups to go")
	parser.add_argument("-c", "--cron", help="Use this when running from a cron job", action="store_true")
	parser.add_argument("-m", "--mirror", help="Create a bare mirror", action="store_true")
	parser.add_argument("-g", "--git", nargs="+", help="Pass extra arguments to git", default="", metavar="ARGS")
	parser.add_argument("-s", "--suffix", help="Add suffix to repository directory names", default="")
	parser.add_argument("-p", "--password", help="Authenticate with Github API")
	parser.add_argument("-t", "--token", help="OAuth token for authentification")

	return parser

def process_repo(repo, args):
	if not args.cron:
		print("Processing repo: %s"%(repo.full_name))

	dir = "%s/%s" % (args.backupdir, repo.name + args.suffix)
	config = "%s/%s" % (dir, "config" if args.mirror else ".git/config")

	if not os.access(config, os.F_OK):
		if not args.cron:
			print("Repo doesn't exists, lets clone it")

		clone_repo(repo, dir, args)
	else:
		if not args.cron:
			print("Repo already exists, let's try to update it instead")

	update_repo(repo, dir, args)


def clone_repo(repo, dir, args):
	if args.mirror:
		git("clone", ["--mirror", repo.git_url, dir], args.git, dir)
	else:
		git("clone", [repo.git_url, dir], args.git, dir)


def update_repo(repo, dir, args):
	# GitHub => Local
	# TODO: use subprocess package and fork git into background (major performance boost expected)
	if args.mirror:
		git("fetch", ["--prune"], args.git, dir)
	else:
		git("pull", gargs=args.git, gdir=dir)

	# Fetch description and owner (useful for gitweb, cgit etc.)
	if repo.description:
		git("config", ["--local", "gitweb.description", "%s" % (repo.description.encode("utf-8"))], gdir=dir)

	if repo.user.name and repo.user.email:
		git("config", ["--local", "gitweb.owner", "%s <%s>" % (repo.user.name.encode("utf-8"), repo.user.email.encode("utf-8"))], gdir=dir)

	git("config", ["--local", "cgit.name", str(repo.name)], gdir=dir)
	git("config", ["--local", "cgit.defbranch", str(repo.default_branch)], gdir=dir)
	git("config", ["--local", "cgit.clone-url", str(repo.clone_url)], gdir=dir)


def git(gcmd, args=[], gargs=[], gdir=""):
	cmd = ["git"]
	if (gdir):
		cmd.append("--git-dir")
		cmd.append(gdir)
	cmd.append(gcmd)
	cmd.extend(gargs)
	cmd.extend(args)

	subprocess.call(cmd)

if __name__ == "__main__":
	main()
