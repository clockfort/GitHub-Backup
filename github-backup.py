#!/usr/bin/env python

"""
Authors: Anthony Gargiulo (anthony@agargiulo.com)
         Steffen Vogel (post@steffenvogel.de)

Created: Fri Jun 15 2012
"""


from argparse import ArgumentParser
import subprocess
import os, os.path
import logging
import github

LOGGER = logging.getLogger('github-backup')

def main():
    logging.basicConfig(level=logging.INFO)


    parser = init_parser()
    args = parser.parse_args()

    if args.quiet:
        LOGGER.setLevel(logging.WARN)
    elif args.debug:
        LOGGER.setLevel(logging.DEBUG)
        github.enable_console_debug_logging()

    # Process args
    if args.quiet:
        args.git.append("--quiet")

    args.backupdir = args.backupdir.rstrip("/")

    # Make the connection to Github here.
    config = {'login_or_token': args.login_or_token}

    if args.password:
        config['password'] = args.password

    gh = github.Github(**config)

    # Check that backup dir exists
    if not os.path.exists(args.backupdir):
        os.mkdir(args.backupdir)

    # Get all repos
    filters = {
        'affiliation': ','.join(args.affiliation),
        'visibility': args.visibility
    }

    if args.organization:
        org = gh.get_org(args.org)
        repos = org.get_repos(**filters)
    else:
        user = gh.get_user()
        repos = user.get_repos(**filters)

    for repo in repos:
        if args.skip_forks and repo.fork:
            continue

        process_repo(repo, args)

def init_parser():
    """Set up the argument parser."""

    parser = ArgumentParser(description="makes a backup of all of a github user's repositories")

    parser.add_argument("login_or_token", help="A Github username or token")
    parser.add_argument("backupdir", help="The folder where you want your backups to go")
    parser.add_argument("-v", "--visibility", help="Filter repos by their visibility", choices=['all', 'public', 'private'], default='all')
    parser.add_argument("-a", "--affiliation", help="Filter repos by their affiliation", action='append', type=str, default=['owner'], choices=['owner', 'collaborator', 'organization_member'])
    parser.add_argument("-d", "--debug", help="Show debug info", action="store_true")
    parser.add_argument("-q", "--quiet", help="Only show errors", action="store_true")
    parser.add_argument("-m", "--mirror", help="Create a bare mirror", action="store_true")
    parser.add_argument("-f", "--skip-forks", help="Skip forks", action="store_true")
    parser.add_argument("-g", "--git", nargs="+", help="Pass extra arguments to git", type=list, default=[], metavar="ARGS")
    parser.add_argument("-t", "--type", help="Select the protocol for cloning", choices=['git', 'http', 'ssh'], default='ssh')
    parser.add_argument("-s", "--suffix", help="Add suffix to repository directory names", default="")
    parser.add_argument("-p", "--password", help="Authenticate with Github API")
    parser.add_argument("-P", "--prefix", help="Add prefix to repository directory names", default="")
    parser.add_argument("-o", "--organization", help="Backup Organizational repositories", metavar="ORG")

    return parser


def process_repo(repo, args):
    LOGGER.info("Processing repo: %s", repo.full_name)

    dir = args.backupdir + '/' + args.prefix + repo.name + args.suffix
    config = "%s/%s" % (dir, "config" if args.mirror else ".git/config")

    if not os.access(config, os.F_OK):
        LOGGER.info("Repo doesn't exists, lets clone it")
        clone_repo(repo, dir, args)
    else:
        LOGGER.info("Repo already exists, let's try to update it instead")
        update_repo(repo, dir, args)


def clone_repo(repo, dir, args):
    if args.type == 'http':
        url = repo.clone_url
    elif args.type == 'ssh':
        url = repo.ssh_url
    elif args.type == 'git':
        url = repo.git_url

    git_args = [url, os.path.basename(dir)]
    if args.mirror:
        git_args.insert(0, '--mirror')

    git("clone", git_args, args.git, args.backupdir)


def update_repo(repo, dir, args):
    # GitHub => Local
    # TODO: use subprocess package and fork git into
    #       background (major performance boost expected)
    if args.mirror:
        git("fetch", ["--prune"], args.git, dir)
    else:
        git("pull", gargs=args.git, gdir=dir)

    # Fetch description and owner (useful for gitweb, cgit etc.)
    if repo.description:
        git("config", ["--local", "gitweb.description",
            repo.description.encode("utf-8")], gdir=dir)

    if repo.owner.name and repo.owner.email:
        owner = "%s <%s>" % (repo.owner.name.encode("utf-8"),
                             repo.owner.email.encode("utf-8"))
        git("config", ["--local", "gitweb.owner", owner], gdir=dir)

    git("config", ["--local", "cgit.name", str(repo.name)], gdir=dir)
    git("config", ["--local", "cgit.defbranch", str(repo.default_branch)], gdir=dir)
    git("config", ["--local", "cgit.clone-url", str(repo.clone_url)], gdir=dir)


def git(gcmd, args=[], gargs=[], gdir=""):
    cmd = ["git"]
    if gdir:
        cmd.extend(["-C", gdir])
    cmd.append(gcmd)
    cmd.extend(gargs)
    cmd.extend(args)

    print(cmd)
    subprocess.call(cmd)

if __name__ == "__main__":
    main()
