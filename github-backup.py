#!/usr/bin/env python

"""
Authors: Anthony Gargiulo (anthony@agargiulo.com)
         Steffen Vogel (post@steffenvogel.de)

Created: Fri Jun 15 2012
"""


import os
import errno
import codecs
import json
import subprocess
import logging
from argparse import ArgumentParser

import requests
import github

LOGGER = logging.getLogger('github-backup')

IsAuthorized = False

def main():
    global IsAuthorized
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
    if args.include_everything:
        args.account = True
        args.include_starred = True
        args.include_watched = True
        args.include_followers = True
        args.include_following = True
    if args.include_starred or args.include_watched or args.include_followers \
       or args.include_following:
        args.account = True

    args.backupdir = args.backupdir.rstrip("/")

    # Make the connection to Github here.
    config = {}
    if args.password:
        config = {'login_or_token': args.login_or_token}
        config['password'] = args.password
    else:
        # unauthenticated users can only use http git method
        args.type = 'http'

    gh = github.Github(**config)

    # Check that backup dir exists
    if not os.path.exists(args.backupdir):
        mkdir_p(args.backupdir)

    if args.organization:
        if args.password:
            account = gh.get_organization(args.org)
        else:
            account = gh.get_organization(args.login_or_token)
    else:
        if args.password:
            account = gh.get_user(args.username)
        else:
            account = gh.get_user(args.username or args.login_or_token)

    IsAuthorized = isinstance(account, github.AuthenticatedUser.AuthenticatedUser)

    filters = {}
    if IsAuthorized:
        # Get all repos
        filters = {
            'affiliation': ','.join(args.affiliation),
            'visibility': args.visibility
        }

    if args.account:
        process_account(gh, account, args)

    repos = account.get_repos(**filters)
    for repo in repos:
        if args.skip_forks and repo.fork:
            continue

        process_repo(repo, args)

def init_parser():
    """Set up the argument parser."""

    parser = ArgumentParser(description="makes a backup of a github user's account")

    parser.add_argument("login_or_token", help="A Github username or token for authenticating")
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
    parser.add_argument("-u", "--username", help="Backup USER account", metavar="USER")
    parser.add_argument("-p", "--password", help="Authenticate with Github API")
    parser.add_argument("-P", "--prefix", help="Add prefix to repository directory names", default="")
    parser.add_argument("-o", "--organization", help="Backup Organizational repositories", metavar="ORG")
    parser.add_argument("-A", "--account", help="Backup account data", action='store_true')
    parser.add_argument('--all',
                        action='store_true',
                        dest='include_everything',
                        help='include everything in backup (not including [*])')
    parser.add_argument('--starred',
                        action='store_true',
                        dest='include_starred',
                        help='include JSON output of starred repositories in backup')
    parser.add_argument('--watched',
                        action='store_true',
                        dest='include_watched',
                        help='include JSON output of watched repositories in backup')
    parser.add_argument('--followers',
                        action='store_true',
                        dest='include_followers',
                        help='include JSON output of followers in backup')
    parser.add_argument('--following',
                        action='store_true',
                        dest='include_following',
                        help='include JSON output of following users in backup')

    return parser

def fetch_url(url, outfile):
    headers = {
        "User-Agent": "PyGithub/Python"
    }
    with open(outfile, 'w') as f:
        f.write(requests.get(url, headers=headers).content)

def process_account(gh, account, args):
    LOGGER.info("Processing account: %s", account.login)

    dir = os.path.join(args.backupdir, 'account')
    if not os.access(dir, os.F_OK):
        mkdir_p(dir)

    account_file = os.path.join(dir, 'account.json')
    with codecs.open(account_file, 'w', encoding='utf-8') as f:
        json_dump(account.raw_data, f)

    if IsAuthorized:
        emails_file = os.path.join(dir, 'emails.json')
        with codecs.open(emails_file, 'w', encoding='utf-8') as f:
            json_dump(list(account.get_emails()), f)

    if args.include_starred:
        LOGGER.debug("    Getting starred repository list")
        fetch_url(account.starred_url, os.path.join(dir, 'starred.json'))

    if args.include_watched:
        LOGGER.debug("    Getting watched repository list")
        fetch_url(account.subscriptions_url, os.path.join(dir, 'watched.json'))

    if args.include_followers:
        LOGGER.debug("    Getting followers repository list")
        fetch_url(account.followers_url, os.path.join(dir, 'followers.json'))

    if args.include_following:
        LOGGER.debug("    Getting following repository list")
        fetch_url(account.following_url, os.path.join(dir, 'following.json'))


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

    if isinstance(repo, github.Gist.Gist):
        # Save extra gist info
        gist_file = os.path.join(os.path.dirname(dir), repo.id+'.json')
        with codecs.open(gist_file, 'w', encoding='utf-8') as f:
            json_dump(repo.raw_data, f)


def clone_repo(repo, dir, args):
    if args.type == 'http' or not IsAuthorized:
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

def json_dump(data, output_file):
    json.dump(data,
              output_file,
              ensure_ascii=False,
              sort_keys=True,
              indent=4,
              separators=(',', ': '))

def mkdir_p(path):
    head, tail = os.path.split(path)
    if head and not os.access(head, os.F_OK):
        mkdir_p(head)

    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

if __name__ == "__main__":
    main()
