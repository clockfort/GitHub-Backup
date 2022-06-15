# GitHub-Backup

## Description

GitHub-Backup makes a local backup copy of all of a github user's (or github organization's) repositories.

## Dependencies

GitHub-Backup requires the `PyGitHub` Python package for the GitHub API v3.

Installation is simple with

```bash
pip install git+https://github.com/clockfort/GitHub-Backup
```

## Usage

```
usage: github-backup.py [-h] [-v {all,public,private}] [-a {owner,collaborator,organization_member}] [-d] [-q] [-m] [-f] [--skip-repos] [-g ARGS [ARGS ...]] [-t {git,http,ssh}] [-s SUFFIX] [-u USER] [-p [PASSWORD]]
                        [-P PREFIX] [-o ORG] [-A] [--all] [--starred] [--watched] [--followers] [--following] [--issues] [--issue-comments] [--issue-events] [--pulls] [--pull-comments] [--pull-commits] [--keys]
                        [--wikis] [--gists] [--starred-gists] [--releases] [--assets]
                        login_or_token backupdir

makes a backup of a github user's account

positional arguments:
  login_or_token        A Github username or token for authenticating
  backupdir             The folder where you want your backups to go

optional arguments:
  -h, --help            show this help message and exit
  -v {all,public,private}, --visibility {all,public,private}
                        Filter repos by their visibility
  -a {owner,collaborator,organization_member}, --affiliation {owner,collaborator,organization_member}
                        Filter repos by their affiliation
  -d, --debug           Show debug info
  -q, --quiet           Only show errors
  -m, --mirror          Create a bare mirror
  -f, --skip-forks      Skip forks
  --skip-repos          Skip backing up repositories
  -g ARGS [ARGS ...], --git ARGS [ARGS ...]
                        Pass extra arguments to git
  -t {git,http,ssh}, --type {git,http,ssh}
                        Select the protocol for cloning
  -s SUFFIX, --suffix SUFFIX
                        Add suffix to repository directory names
  -u USER, --username USER
                        Backup USER account
  -p [PASSWORD], --password [PASSWORD]
                        Authenticate with Github API (give no argument to check ~/.github-backup.conf or prompt for a password)
  -P PREFIX, --prefix PREFIX
                        Add prefix to repository directory names
  -o ORG, --organization ORG
                        Backup Organizational repositories
  -A, --account         Backup account data
  --all                 include everything in backup (not including [*])
  --starred             include JSON output of starred repositories in backup
  --watched             include JSON output of watched repositories in backup
  --followers           include JSON output of followers in backup
  --following           include JSON output of following users in backup
  --issues              include issues in backup
  --issue-comments      include issue comments in backup
  --issue-events        include issue events in backup
  --pulls               include pull requests in backup
  --pull-comments       include pull request review comments in backup
  --pull-commits        include pull request commits in backup
  --keys                include ssh keys in backup
  --wikis               include wiki clone in backup
  --gists               include gists in backup [*]
  --starred-gists       include starred gists in backup [*]
  --releases            include release information, not including assets or binaries
  --assets              include assets alongside release information; only applies if including releases
```

Then, put it in a cron job somewhere and forget about it for eternity.

## How-to back up entire GitHub organisation repos

1. Install Dependencies: `sudo pip install pygithub3`
2. Clone this repo using `$ git clone https://github.com/clockfort/GitHub-Backup.git`
3. Just open the cloned repo folder and run the terminal:

```bash
./github-backup.py [Organization Name] [Path To Saving Directory] -o [Organization Name]
```

Example:

```bash
github-backup LineageOS /home/mohamed786/githubbak -o LineageOS
```

## Use a a personal access token (PAT) instead of your password

You can generate a dedicated personal access token instead of using your GitHub password.

Follow the steps described [here in the GitHub documentation](https://docs.github.com/en/github/authenticating-to-github/creating-a-personal-access-token) and use the token instead of your password.
Using a PAT can also work around issues when two factor authentication (TFA) is enabled on your account.


## Why this software exists

This software is useful in many cases:

  - GitHub suddenly explodes.
  - GitHub goes out of business.
  - Your corporation's backup policies are more stringent than GitHub's.
  - You have spotty/no internet access - perhaps you'd like to have all of your repositories available to code on while you ride the train?
  - You are paranoid tinfoil-hat wearer who needs to back up everything in triplicate on a variety of outdated tape media.


## Questions, Improvements, Etc

If you have any improvements, I'm happy, (grateful, in fact) to entertain pull requests/patches, just drop me a line or message me on GitHub.

## Contributors

Idea/original implementation by 

- Chris Lockfort (clockfort@csh.rit.edu) (Github: Clockfort)
  (Original idea)

- Anthony Gargiulo (anthony@agargiulo.com) (Github: agargiulo)
  (Python version)

- Steffen Vogel (post@steffenvogel.de) (Github: stv0g)
  (A lot of patches and improvements)
