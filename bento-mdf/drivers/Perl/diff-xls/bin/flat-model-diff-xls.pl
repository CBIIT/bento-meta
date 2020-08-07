#!/usr/bin/env perl
use v5.10;
use Excel::Writer::XLSX;
use File::Spec;
use Cwd qw/realpath/;
use Getopt::Long;
use Pod::Usage;
use IPC::Run qw/run/;
use Carp qw/croak/;
$VERSION = '0.1';

use strict;
use warnings;


my ($last_change,$commits,$skip,$outf,$working);

GetOptions( "commits:s" => \$commits,
            "skip:i" => \$skip,
            "outfile:s" => \$outf,
            "working" => \$working,
           ) or pod2usage(1);


my $gitdir = get_git_dir();
unless ($gitdir && -d File::Spec->catdir($gitdir,'docs','model-desc') ) {
  say "This doesn't look like a Bento model repo.";
  say "Need to have a 'docs/model-desc' directory that contains a <model>.txt file.";
  exit(1);
}
my $mddir = File::Spec->catdir($gitdir,'docs','model-desc');
opendir my $d, $mddir or die $!;
my ($flatfile) = grep /^.*model.txt$/, readdir $d;

unless ($flatfile) {
  say "Can't find a <model>.txt file in docs/model-desc.";
  exit(1);
}

my $flatpath = File::Spec->catfile($mddir,$flatfile);

open my $ct, $flatpath  or die "$flatfile: $!";
my $lines=0;
while (<$ct>) { $lines++; }
$lines *= 2;

my $gitlog = ['git', 'log', '-1',
              "-U$lines",
              '--pretty=format:Date:%aI\|Commit:%h',
              ($commits ? $commits : ()),
              ($skip ? ('--skip',$skip) : ()),
              $flatpath];
my ($in, $gitlog_out, $err);
my $rc = run $gitlog, \$in, \$gitlog_out, \$err;
unless ($rc) {
  say "git log returned error:";
  say $err;
  exit(1);
}

my @inf = split /\n/, $gitlog_out;
my ($commit, $date);
if ($working) {
  # create diff between working file and desired commit
  # this is mainly for Travis build and commit to ghpages
  my $commit;
  for (@inf) {
    /Commit/ && do {
      ($commit) = /\|Commit:([0-9a-f]+)/;
      last;
    };
  }
  die "Couldn't find commit in git log output" unless $commit;
  run ['date','+%Y-%m-%dT%H_%M_%S'],'>',\$date;
  chomp $date;
  $gitlog_out = $err = '';
  $rc = run [split(/ /,"git diff -U$lines $commit $flatpath")], \$in, \$gitlog_out, \$err;
  unless ($rc) {
    say "git diff returned error:";
    say $err;
    exit(1);
  }
  @inf = split /\n/,$gitlog_out;
}

my %moved;
my $past_hdr;
my @lines;
for (@inf) {
  /^Date/ && ( ($date) = /Date:(.*)\+/ );
  /repo/ && ($past_hdr = 1);
  next unless $past_hdr;
  chomp;
  push @lines, $_;
  if (/^[+-](.*)$/) {
    $moved{$1}++;
  }
}
for (keys %moved) {
  delete $moved{$_} unless $moved{$_} > 1;
}
1;

@lines = map {
  /^([+-])(.*)$/;
  no warnings 'uninitialized';
  $moved{$2} ?
    (($1 eq '-') ? () : " $2" ) :
    $_;
} @lines;
undef $past_hdr;
my @maxlen = (0,0,0);

$flatfile =~ /^(.*)\./;
$outf //= "diff-$1-$date.xlsx";
$outf =~ s/:/_/g;

my $wb = Excel::Writer::XLSX->new($outf);
my $ws = $wb->add_worksheet;
my $norm_fmt = $wb->add_format();
my $del_fmt = $wb->add_format(
  font_strikeout => 1
 );
my $add_fmt = $wb->add_format(
  bg_color => 'yellow'
 );

  
my $r=1;
for (@lines) {
  /^.node/ && ($past_hdr=1);
  my $fmt =  $norm_fmt;
  if (/^-/) {
    $fmt = $del_fmt;
  }
  elsif (/^\+/) {
    $fmt = $add_fmt;
  }
  s/^.//;
  
  if ($past_hdr) {
    my @col = split /\t/;
    for my $i (0..$#col) {
      no warnings 'uninitialized';
      $maxlen[$i] = ( $maxlen[$i] > length $col[$i] ?
			$maxlen[$i] :
			length $col[$i]);
    }
  }
  $ws->write("A$r", [split /\t/], $fmt);
  $r++;
}
for my $i (0..$#maxlen) {
  $ws->set_column($i, $i, $maxlen[$i]);
}
$wb->close;

# find the top level directory and return absolute dir
sub get_git_dir {
  my $dir = '.';
  while ( ! -d File::Spec->catdir($dir,'.git') &&
            (realpath($dir) ne File::Spec->rootdir) ) {
    $dir = File::Spec->catdir($dir,'..')
  }
  return if (realpath($dir) eq File::Spec->rootdir);
  return realpath($dir);
}

=head1 NAME

flat-model-diff-xls.pl - Make a nice Excel showing model flatfile differences

=head1 SYNOPSIS

 Usage: perl flat-model-diff-xls.pl [--commits <commit range>]
                  [--working] [--outfile <output.xls>] [--skip <n>]

 # in a model repo directory:
 # create a diff excel file with the latest changes
 $ perl flat-model-diff-xls.pl # creates diff.xlsx
 # create a diff excel from the previous changeset
 $ perl flat-model-diff-xls.pl --skip 1 # creates diff.xlsx
 # create a diff excel from the commit range in new-diff.xlsx
 $ perl flat-model-diff-xls.pl --commits 51918c8..77bd441 --outfile new-diff.xlsx
 # create a diff excel against the working copy of <model>.txt
 $ perl flat-model-diff-xls.pl --working 

=head1 DESCRIPTION

This script generates an Excel file that tabulates the nodes, relationships, 
properties, and value sets of a Bento model. The Excel file contains rows in 
a strikethrough face to indicate removed records, and rows in a yellow highlight
face to indicate added records. 

"Removed" and "added" are relative to either the last time the model
flatfile was changed (according to C<git log>), the nth-to-last time,
(C<--skip=n>) or according to a pair of commits provided to the
command line option C<--commits>.

This script depends on the existence of the file 

  docs/model-desc/<model-name>model.txt

in the GitHub pages directory of a Bento model repository. This file
should be generated by continuous integration (Travis CI) each time
the model master branch is updated.

=head1 AUTHOR

 Mark A. Jensen < mark -dot- jensen -at- nih -dot- com >
 FNLCR
 2020

=cut
 
