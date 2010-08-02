#!/usr/bin/perl
use strict;
use warnings;
use LWP::Simple;

die "Please supply a github username and backups directory\n" unless (@ARGV == 2);

my $username = $ARGV[0];
my $backupdir = $ARGV[1];
my $page = get("http://github.com/api/v2/yaml/repos/show/$username");
die "Could not complete github API query for $username\n" unless defined $page;

my @list = split(/\n/, $page);
my @urls = grep { /url/ } @list;
my @giturls = grep s/  :url: http/git/, @urls;
@urls = @giturls;
my @reponames = grep s/.*$username\///, @giturls;

for(my $i = 0; $i < @urls; ++$i){
	my $url = $urls[$i];
	my $name = $reponames[$i];
	unless(-e $backupdir){
		system("mkdir $backupdir") and die "Couldn't make $backupdir.\n";
	}
	unless(-e "$backupdir/$name"){ #We haven't backed this up before, let's clone it
		print "CLONING REPOSITORY: $url\n";
		system("cd $backupdir && git clone $url") and die "Encountered an error while git-cloning repository $name\n";
	}
	else{ #We've backed it up before, just fetch the most recent copy
		print "REPOSITORY EXISTED, FETCHING: $name\n";
		system("cd $backupdir/$name && git fetch -q") and die "Encountered an error while git-fetching repository $name\n";
	}
}
