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

	# if both password and token are specified, the token will be
	# used, according to pygithub3 sources
	# however, the username isn't required when using a token
	if (args.token):
		config['token'] = args.token

	gh = Github(**config)

	# Get all of the given user's repos
	if args.organization:
		user_repos = gh.repos.list_by_org(args.organization).all()
	else:
		user_repos = gh.repos.list(user=args.username).all()

	for repo in user_repos:
		repo.user = gh.users.get(repo.owner.login)
		fullrepo = gh.repos.get(repo.owner.login, repo.name)
		if not (args.skip_forks and hasattr(fullrepo, 'parent') and hasattr(fullrepo, 'source')):
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
	parser.add_argument("-f", "--skip-forks", help="Skip forks", action="store_true")
	parser.add_argument("-g", "--git", nargs="+", help="Pass extra arguments to git", default="", metavar="ARGS")
	parser.add_argument("-S", "--ssh", help="Use SSH protocol", action="store_true")
	parser.add_argument("-s", "--suffix", help="Add suffix to repository directory names", default="")
	parser.add_argument("-P", "--prefix", help="Add prefix to repository directory names", default="")
	parser.add_argument("-p", "--password", help="Authenticate with Github API")
	parser.add_argument("-P","--prefix", help="Add prefix to repository directory names", default="")
	parser.add_argument("-o", "--organization", help="Backup Organizational repositories", metavar="ORG")
	parser.add_argument("-t","--token", help="Authenticate with Github API using OAuth token", default="")

	return parser

def process_repo(repo, args):
	if not args.cron:
		print("Processing repo: %s"%(repo.full_name))

	dir = "%s/%s"%(args.backupdir, args.prefix + repo.name + args.suffix)
	config = "%s/%s"%(dir, "config" if args.mirror else ".git/config")

	if not os.access(config, os.F_OK):
		if not args.cron: print("Repo doesn't exists, lets clone it")
		clone_repo(repo, dir, args)
	else:
		if not args.cron: print("Repo already exists, let's try to update it instead")

	update_repo(repo, dir, args)


def clone_repo(repo, dir, args):
	url = repo.ssh_url if args.ssh else repo.git_url

	if args.mirror:
		git("clone", ["--mirror", url, dir], args.git, dir)
	else:
		git("clone", [url, dir], args.git, dir)

def update_repo(repo, dir, args):
	# GitHub => Local
	# TODO: use subprocess package and fork git into background (major performance boost expected)
	if args.mirror:
		git("fetch", ["--prune"], args.git, dir)
	else:
		git("pull", gargs=args.git, gdir=dir)

	# Fetch description and owner (useful for gitweb, cgit etc.)
	if repo.description:
		git("config", ["--local", "gitweb.description", repo.description], gdir=dir)
	if repo.user.name and repo.user.email:
		git("config", ["--local", "gitweb.owner", "%s <%s>" %(repo.user.name, repo.user.email.encode("utf-8"))], gdir=dir)
	git("config", ["--local", "cgit.name", repo.name], gdir=dir)
	git("config", ["--local", "cgit.defbranch", repo.default_branch], gdir=dir)
	git("config", ["--local", "cgit.clone-url", repo.clone_url], gdir=dir)


def git(gcmd, args=[], gargs=[], gdir=""):
	cmd = ["git"]
	if gdir:
		cmd.append("--git-dir")
		cmd.append(gdir)
	cmd.append(gcmd)
	cmd.extend(gargs)
	cmd.extend(args)

	subprocess.call(cmd)
>>>>>>> replaced os.system() by subprocess.call() and fixed escaping errors

if __name__ == "__main__":
	main()
