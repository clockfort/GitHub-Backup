GitHub-Backup
============================

Description
----------------------------

GitHub-Backup makes a local backup copy of all of a github user's (or github organization's) repositories.

Dependencies
----------------------------

GitHub-Backup requires `pygithub3` a Python library for the GitHub API v3.

Installation is simple with

	pip install pygithub3

Usage
----------------------------
````
usage: github-backup.py [-h] [-c] [-m] [-S] [-g ARGS] [-s SUFFIX] [-P PREFIX]
                        [-p PASSWORD] [-t TOKEN] [-o ORG]
                        username backupdir

makes a backup of all of a github user's repositories

positional arguments:
  username              A Github username
  backupdir             The folder where you want your backups to go

optional arguments:
  -h, --help            show this help message and exit
  -c, --cron            Use this when running from a cron job
  -m, --mirror          Create a bare mirror
  -S, --ssh             Use SSH protocol
  -g ARGS, --git ARGS   Pass extra arguments to git
  -s SUFFIX, --suffix SUFFIX
                        Add suffix to repository directory names
  -P PREFIX, --prefix PREFIX
                        Add prefix to repository directory names
  -p PASSWORD, --password PASSWORD
                        Authenticate with Github API
  -t TOKEN, --token TOKEN
                        OAuth token for authentification
  -o ORG, --organization ORG
                        Backup Organizational repositories
````

Then, put it in a cron job somewhere and forget about it for eternity.

Why This Software Exists
-------------------------
This software is useful in many cases:

  - GitHub suddenly explodes.

  - GitHub goes out of business.

  - Your corporation's backup policies are more stringent than GitHub's.

  - You have spotty/no internet access - perhaps you'd like to have all of your repositories available to code on while you ride the train?

  - You are paranoid tinfoil-hat wearer who needs to back up everything in triplicate on a variety of outdated tape media.


Questions, Improvements, Etc
-----------------------------

If you have any improvements, I'm happy, (grateful, in fact) to entertain pull requests/patches, just drop me a line or message me on GitHub.

Contributors
----------------------------

Idea/original implementation by 

- Chris Lockfort (clockfort@csh.rit.edu) (Github: Clockfort)
  (Original idea)

- Anthony Gargiulo (anthony@agargiulo.com) (Github: agargiulo)
  (Python version)

- Steffen Vogel (post@steffenvogel.de) (Github: stv0g)
  (A lot of patches and improvements)
