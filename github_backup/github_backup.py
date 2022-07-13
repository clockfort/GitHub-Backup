#!/usr/bin/env python

"""
Authors: Anthony Gargiulo (anthony@agargiulo.com)
         Steffen Vogel (post@steffenvogel.de)
         Glenn Washburn (development@efficientek.com)

Created: Fri Jun 15 2012
"""


import os
import re
import errno
import codecs
import json
import itertools
import subprocess
import logging
import getpass
from datetime import datetime, timezone
import time
try: #PY3
    from configparser import SafeConfigParser as ConfigParser
except ImportError:
    from ConfigParser import SafeConfigParser as ConfigParser
from argparse import ArgumentParser

import requests
import github
from github import RateLimitExceededException

LOGGER = logging.getLogger('github-backup')

IS_AUTHORIZED = False
CONFFILE = os.path.join(os.getenv('HOME'), '.github-backup.conf')

def main():
    global IS_AUTHORIZED
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
        args.include_issues = True
        args.include_issue_comments = True
        args.include_issue_events = True
        args.include_pulls = True
        args.include_pull_comments = True
        args.include_pull_commits = True
        args.include_keys = True
        args.include_releases = True
        args.include_assets = True
        args.include_wiki = True
    if args.include_starred or args.include_watched or args.include_followers \
       or args.include_following or args.include_keys:
        args.account = True

    args.backupdir = args.backupdir.rstrip("/")

    # Make the connection to Github here.
    config = {'login_or_token': args.login_or_token}
    if args.password == False:
        # no password option given, continue unauthenticated
        # unauthenticated users can only use http git method
        args.type = 'http'
    elif args.password == None:
        # password option given, but no password value given
        if os.path.isfile(CONFFILE):
            cfg = ConfigParser()
            cfg.read(CONFFILE)
            try:
                config['password'] = cfg.get('github-backup', 'APITOKEN')
            except:
                config['password'] = cfg.get('github-backup', 'PASSWORD')
        else:
            password = getpass.getpass('Enter password for {}: '.format(config['login_or_token']))
            if password:
                config['password'] = password
    else:
        config['password'] = args.password

    LOGGER.debug("Github config: %r", config)
    global gh
    gh = github.Github(**config)

    # Check that backup dir exists
    if not os.path.exists(args.backupdir):
        mkdir_p(args.backupdir)

    while True:
        try:
            if args.organization:
                account = gh.get_organization(args.organization)
            else:
                if args.username:
                    account = gh.get_user(args.username)
                elif config.get('password', None):
                    account = gh.get_user()
                else:
                    account = gh.get_user(args.login_or_token)

            break
        except github.BadCredentialsException:
            LOGGER.info("Given login_or_token is not authenticated, ignoring...")
            # Reset gh client, try without auth
            gh = github.Github()

    IS_AUTHORIZED = isinstance(account, (github.AuthenticatedUser.AuthenticatedUser, github.Organization.Organization))
    assert (bool(config.get('password', None)) or IS_AUTHORIZED), account

    if args.include_keys and not IS_AUTHORIZED:
        LOGGER.info("Cannot backup keys with unauthenticated account, ignoring...")
        args.include_keys = False

    filters = {}
    if isinstance(account, github.AuthenticatedUser.AuthenticatedUser):
        # Get all repos
        filters = {
            'affiliation': ','.join(args.affiliation),
            'visibility': args.visibility
        }

    if args.account:
        process_account(gh, account, args)

    if args.include_gists:
        for gist in get_account_gists(account):
            RepositoryBackup(gist, args).backup()

    if args.include_starred_gists and hasattr(account, 'get_starred_gists'):
        for gist in get_account_starred_gists(account):
            RepositoryBackup(gist, args).backup()

    if not args.skip_repos:
        repos = get_account_repos(account, **filters) 
        for repo in repos:
            if args.skip_forks and repo.fork:
                continue

            RepositoryBackup(repo, args).backup()

def rate_limited_retry():
    def decorator(func):
        def ret(*args, **kwargs):
            for _ in range(3):
                try:
                    return func(*args, **kwargs)
                except RateLimitExceededException:
                    limits = gh.get_rate_limit()
                    print(f"Rate limit exceeded")
                    print("Search:", limits.search, "Core:", limits.core, "GraphQl:", limits.graphql)
                    
                    if limits.search.remaining == 0:
                        limited = limits.search
                    elif limits.graphql.remaining == 0:
                        limited = limits.graphql
                    else:
                        limited = limits.core
                    reset = limited.reset.replace(tzinfo=timezone.utc)
                    now = datetime.now(timezone.utc)
                    seconds = (reset - now).total_seconds() + 30
                    print(f"Reset is in {seconds} seconds.")
                    if seconds > 0.0:
                        print(f"Waiting for {seconds} seconds...")
                        time.sleep(seconds)
                        print("Done waiting - resume!")
            raise Exception("Failed too many times")
        return ret
    return decorator

@rate_limited_retry()
def get_search_issues(gh, author, type):
    _issues = list(gh.search_issues('', author=author, type=type))
    return _issues

@rate_limited_retry()
def get_issue_comments(issue):
    return list(issue.get_comments())

@rate_limited_retry()
def get_issue_events(issue):
    return list(issue.get_events())

@rate_limited_retry()
def get_issue_as_pull_request(issue):
    return issue.as_pull_request()

@rate_limited_retry()
def get_issue_commits(issue):
    return list(issue.get_commits())

@rate_limited_retry()
def get_repo_releases(repo):
    return list(repo.get_releases())

@rate_limited_retry()
def get_release_assets(release):
    return list(release.get_assets())

@rate_limited_retry()
def get_repo_issues(repo, state):
    return list(repo.get_issues(state=state))

@rate_limited_retry()
def get_repo_pulls(repo, state):
    return list(repo.get_pulls(state=state))

@rate_limited_retry()
def get_account_login(account):
    return account.login

@rate_limited_retry()
def get_comment_raw_data(comment):
    return comment.raw_data

@rate_limited_retry()
def get_release_raw_data(release):
    return release.raw_data

@rate_limited_retry()
def get_commit_raw_data(commit):
    return commit.raw_data

@rate_limited_retry()
def get_repo_raw_data(repo):
    return repo.raw_data

@rate_limited_retry()
def get_event_raw_data(event):
    return event.raw_data

@rate_limited_retry()
def get_account_raw_data(account):
    return account.raw_data

@rate_limited_retry()
def get_key_raw_data(key):
    return key.raw_data

@rate_limited_retry()
def get_issue_raw_data(issue):
    return issue.raw_data

@rate_limited_retry()
def get_account_emails(account):
    return account.get_emails()

@rate_limited_retry()
def get_account_starred_urls(account):
    return account.starred_url

@rate_limited_retry()
def get_account_subscriptions_url(account):
    return account.subscriptions_url

@rate_limited_retry()
def get_account_followers_url(account):
    return account.followers_url

@rate_limited_retry()
def get_account_following_url(account):
    return account.following_url

@rate_limited_retry()
def get_account_keys(account):
    return list(account.get_keys())

@rate_limited_retry()
def get_account_gists(account):
    return list(account.get_gists())

@rate_limited_retry()
def get_account_starred_gists(account):
    return list(account.get_starred_gists())

@rate_limited_retry()
def get_account_repos(account, **filters):
    return list(account.get_repos(**filters))

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
    parser.add_argument("--skip-repos", help="Skip backing up repositories", action="store_true")
    parser.add_argument("-g", "--git", help="Pass extra arguments to git", action='append', default=[], metavar="ARGS")
    parser.add_argument("-t", "--type", help="Select the protocol for cloning", choices=['git', 'http', 'ssh'], default='ssh')
    parser.add_argument("-s", "--suffix", help="Add suffix to repository directory names", default="")
    parser.add_argument("-u", "--username", help="Backup USER account", metavar="USER")
    parser.add_argument("-p", "--password", help="Authenticate with Github API (give no argument to check ~/.github-backup.conf or prompt for a password)", nargs="?", default=False)
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
    parser.add_argument('--issues',
                        action='store_true',
                        dest='include_issues',
                        help='include issues in backup')
    parser.add_argument('--issue-comments',
                        action='store_true',
                        dest='include_issue_comments',
                        help='include issue comments in backup')
    parser.add_argument('--issue-events',
                        action='store_true',
                        dest='include_issue_events',
                        help='include issue events in backup')
    parser.add_argument('--pulls',
                        action='store_true',
                        dest='include_pulls',
                        help='include pull requests in backup')
    parser.add_argument('--pull-comments',
                        action='store_true',
                        dest='include_pull_comments',
                        help='include pull request review comments in backup')
    parser.add_argument('--pull-commits',
                        action='store_true',
                        dest='include_pull_commits',
                        help='include pull request commits in backup')
    parser.add_argument('--keys',
                        action='store_true',
                        dest='include_keys',
                        help='include ssh keys in backup')
    parser.add_argument('--wikis',
                        action='store_true',
                        dest='include_wiki',
                        help='include wiki clone in backup')
    parser.add_argument('--gists',
                        action='store_true',
                        dest='include_gists',
                        help='include gists in backup [*]')
    parser.add_argument('--starred-gists',
                        action='store_true',
                        dest='include_starred_gists',
                        help='include starred gists in backup [*]')
    parser.add_argument('--releases',
                        action='store_true',
                        dest='include_releases',
                        help='include release information, not including assets or binaries'
                        )
    parser.add_argument('--assets',
                        action='store_true',
                        dest='include_assets',
                        help='include assets alongside release information; only applies if including releases')

    return parser

def fetch_url(url, outfile):
    headers = {
        "User-Agent": "PyGithub/Python"
    }
    with open(outfile, 'w') as f:
        resp = requests.get(url, headers=headers)
        LOGGER.debug("GET %s %r ==> %d %r", url, headers, resp.status_code, resp.headers)
        f.write(resp.content.decode(resp.encoding or 'utf-8'))

def process_account(gh, account, args):
    LOGGER.info("Processing account: %s", get_account_login(account))

    dir = os.path.join(args.backupdir, 'account')
    if not os.access(dir, os.F_OK):
        mkdir_p(dir)

    account_file = os.path.join(dir, 'account.json')
    with codecs.open(account_file, 'w', encoding='utf-8') as f:
        json_dump(get_account_raw_data(account), f)

    if IS_AUTHORIZED:
        emails_file = os.path.join(dir, 'emails.json')
        with codecs.open(emails_file, 'w', encoding='utf-8') as f:
            json_dump(list(get_account_emails(account)), f)

    if args.include_starred:
        LOGGER.info("    Getting starred repository list")
        fetch_url(get_account_starred_urls(account), os.path.join(dir, 'starred.json'))

    if args.include_watched:
        LOGGER.info("    Getting watched repository list")
        fetch_url(get_account_subscriptions_url(account), os.path.join(dir, 'watched.json'))

    if args.include_followers:
        LOGGER.info("    Getting followers repository list")
        fetch_url(get_account_followers_url(account), os.path.join(dir, 'followers.json'))

    if args.include_following:
        LOGGER.info("    Getting following repository list")
        fetch_url(get_account_following_url(account), os.path.join(dir, 'following.json'))

    if args.include_keys:
        LOGGER.info("    Getting keys")
        for key in get_account_keys(account):
            key_dir = os.path.join(dir, 'keys')
            if not os.access(key_dir, os.F_OK):
                mkdir_p(key_dir)
            key_file = os.path.join(key_dir, key.title+'.json')
            with codecs.open(key_file, 'w', encoding='utf-8') as f:
                json_dump(get_key_raw_data(key), f)

    filters = ('assigned', 'created')

    if args.include_issues:
        LOGGER.info("    Getting issues for user %s", get_account_login(account))
        issues = []
        for filter in filters:
            _issues = get_search_issues(gh, get_account_login(account), 'issue')
            issues = itertools.chain(issues, _issues)

        RepositoryBackup._backup_issues(issues, args, dir)

    if args.include_pulls:
        LOGGER.info("    Getting pull requests for user %s", get_account_login(account))
        issues = []
        for filter in filters:
            _issues = get_search_issues(gh, get_account_login(account), 'pr')
            issues = itertools.chain(issues, _issues)

        RepositoryBackup._backup_pulls(issues, args, dir)


class RepositoryBackup(object):
    def __init__(self, repo, args):
        self.repo = repo
        self.args = args

        self.is_gist = isinstance(repo, github.Gist.Gist)

        if self.is_gist:
            dir = os.path.join(args.backupdir, 'gists', repo.id)
        else:
            dir = os.path.join(args.backupdir, 'repositories', args.prefix + repo.name + args.suffix, 'repository')
        self.dir = dir

        if self.is_gist:
            url = repo.git_pull_url
        elif args.type == 'ssh':
            url = repo.ssh_url
        elif args.type == 'git':
            url = repo.git_url
        elif args.type == 'http' or not IS_AUTHORIZED:
            if re.match('^ghp_.+$', args.login_or_token):
                url = re.sub('^https://', f'https://{args.login_or_token}:x-auth-basic@', repo.clone_url)
            elif args.password:
                if args.username:
                    url = re.sub('^https://', f'https://{args.username}:{args.password}@', repo.clone_url)
                else:
                    url = re.sub('^https://', f'https://{args.login_or_token}:{args.password}@', repo.clone_url)
            else:
                url = repo.clone_url
        self.url = url

        self.wiki_url = None
        if args.include_wiki and repo.has_wiki:
            self.wiki_url = self.url.replace('.git', '.wiki.git')
            self.wiki_dir = os.path.join(args.backupdir, 'repositories', args.prefix + repo.name + args.suffix, 'wiki')

    def backup(self):
        if self.is_gist:
            LOGGER.info("Processing gist: %s", self.repo.id)
        else:
            LOGGER.info("Processing repo: %s", self.repo.full_name)

        config = os.path.join(self.dir, "config" if self.args.mirror else ".git/config")
        if not os.access(os.path.dirname(self.dir), os.F_OK):
            mkdir_p(os.path.dirname(self.dir))
        if not os.access(config, os.F_OK):
            LOGGER.info("Repo doesn't exist, lets clone it")
            self.clone_repo(self.url, self.dir)
        else:
            LOGGER.info("Repo already exists, let's try to update it instead")
            self.update_repo(self.dir)

        if self.wiki_url:
            config = os.path.join(self.wiki_dir, "config" if self.args.mirror else ".git/config")
            if not os.access(os.path.dirname(self.wiki_dir), os.F_OK):
                mkdir_p(os.path.dirname(self.wiki_dir))
            if not os.access(config, os.F_OK):
                LOGGER.info("Wiki repo doesn't exist, lets clone it")
                self.clone_repo(self.wiki_url, self.wiki_dir)
            else:
                LOGGER.info("Wiki repo already exists, let's try to update it instead")
                self.update_repo(self.wiki_dir)

        if self.is_gist:
            # Save extra gist info
            gist_file = os.path.join(os.path.dirname(self.dir), self.repo.id+'.json')
            with codecs.open(gist_file, 'w', encoding='utf-8') as f:
                json_dump(get_repo_raw_data(self.repo), f)
        else:
            if self.args.include_releases:
                self._backup_releases()

            if self.args.include_issues:
                LOGGER.info("    Getting issues for repo %s", self.repo.name)
                #self._backup_issues(self.repo.get_issues(state='all'), self.args, os.path.dirname(self.dir))
                self._backup_issues(get_repo_issues(self.repo, 'all'), self.args, os.path.dirname(self.dir))

            if self.args.include_pulls:
                LOGGER.info("    Getting pull requests for repo %s", self.repo.name)
                #self._backup_pulls(self.repo.get_pulls(state='all'), self.args, os.path.dirname(self.dir))
                self._backup_pulls(get_repo_pulls(self.repo, 'all'), self.args, os.path.dirname(self.dir))

    def clone_repo(self, url, dir):
        git_args = [url, os.path.basename(dir)]
        if self.args.mirror:
            git_args.insert(0, '--mirror')

        git("clone", git_args, self.args.git, os.path.dirname(dir))

    def update_repo(self, dir):
        # GitHub => Local
        # TODO: use subprocess package and fork git into
        #       background (major performance boost expected)
        args, repo = self.args, self.repo
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

        if self.is_gist:
            git("config", ["--local", "cgit.name", str(repo.id)], gdir=dir)
            git("config", ["--local", "cgit.clone-url", str(repo.git_pull_url)], gdir=dir)
        else:
            git("config", ["--local", "cgit.name", str(repo.name)], gdir=dir)
            git("config", ["--local", "cgit.defbranch", str(repo.default_branch)], gdir=dir)
            git("config", ["--local", "cgit.clone-url", str(repo.clone_url)], gdir=dir)

    @classmethod
    def _backup_issues(cls, issues, args, dir):
        for issue in issues:
            project = os.path.basename(os.path.dirname(os.path.dirname(issue.url)))
            issue_data = get_issue_raw_data(issue).copy()
            LOGGER.info("     * %s[%s]: %s", project, issue.number, issue.title)
            if args.include_issue_comments and issue.comments:
                #for comment in issue.get_comments():
                for comment in get_issue_comments(issue):
                    issue_data.setdefault('comment_data', []).append(get_comment_raw_data(comment))
            if args.include_issue_events:
                for event in get_issue_events(issue):
                    issue_data.setdefault('event_data', []).append(get_event_raw_data(event))

            issue_file = os.path.join(dir, 'issues', "{0}:{1}.json".format(project, issue.number))
            if not os.access(os.path.dirname(issue_file), os.F_OK):
                mkdir_p(os.path.dirname(issue_file))
            with codecs.open(issue_file, 'w', encoding='utf-8') as f:
                json_dump(issue_data, f)

    @classmethod
    def _backup_pulls(cls, issues, args, dir):
        for issue in issues:
            project = os.path.basename(os.path.dirname(os.path.dirname(issue.url)))
            if isinstance(issue, github.Issue.Issue):
                issue = get_issue_as_pull_request(issue)
            issue_data = get_issue_raw_data(issue).copy()
            LOGGER.info("     * %s[%s]: %s", project, issue.number, issue.title)
            if args.include_pull_comments and issue.comments:
                for comment in get_issue_comments(issue):
                    issue_data.setdefault('comment_data', []).append(get_comment_raw_data(comment))
            if args.include_pull_commits and issue.commits:
                for commit in get_issue_commits(issue):
                    issue_data.setdefault('commit_data', []).append(get_commit_raw_data(commit))

            issue_file = os.path.join(dir, 'pull-requests', "{0}:{1}.json".format(project, issue.number))
            if not os.access(os.path.dirname(issue_file), os.F_OK):
                mkdir_p(os.path.dirname(issue_file))
            with codecs.open(issue_file, 'w', encoding='utf-8') as f:
                json_dump(issue_data, f)

    def _backup_releases(self):
        for release in get_repo_releases(self.repo):
            rel_dir = os.path.join(os.path.dirname(self.dir), 'releases')
            rel_file = os.path.join(rel_dir, release.tag_name+'.json')
            if not os.access(rel_dir, os.F_OK):
                mkdir_p(rel_dir)
            with codecs.open(rel_file, 'w', encoding='utf-8') as f:
                json_dump(get_release_raw_data(release), f)

            if self.args.include_assets:
                for asset in get_release_assets(release):
                    asset_dir = os.path.join(rel_dir, release.tag_name)
                    asset_file = os.path.join(asset_dir, asset.name)
                    if not os.access(asset_dir, os.F_OK):
                        mkdir_p(asset_dir)
                    fetch_url(asset.browser_download_url, asset_file)
                    assert asset.size == os.path.getsize(asset_file)


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
