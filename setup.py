from setuptools import setup

setup(name='GitHub-Backup',
      version='0.1',
      description='Makes a backup of all of a github user\'s repositories',
      url='https://github.com/clockfort/GitHub-Backup',
      author='Chris Lockfort',
      author_email='clockfort@csh.rit.edu',
      license='CC0-1.0',
      packages=['github_backup'],
      install_requires=[
          'requests',
          'PyGitHub'
      ],
      entry_points = {
        'console_scripts': [
            'github-backup=github_backup.github_backup:main'
        ],
      },
      zip_safe=True)
