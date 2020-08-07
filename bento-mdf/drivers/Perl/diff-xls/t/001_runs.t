use Test::More;
use Test::Exception;
use Cwd qw/realpath/;
use File::Spec;
use IPC::Run qw/run/;

my $t = (-d 't' ? '.' : '..');
my $tool = realpath(File::Spec->catfile($t,'bin','flat-model-diff-xls.pl'));


ok( (-x $tool) , "Found script");
my @cmd = ($^X, $tool);
my ($in,$out,$err);
my $have_git;
lives_ok { run ['git','--help'],'>',\$out and $have_git=1 } "you have git";
lives_ok { run([@cmd,'-h'], \$in, \$out, \$err) } "It runs";
like $out, qr/Usage/, "Usage";
diag $have_git;
SKIP : {
  skip "need git", 1 unless $have_git;
  if (run ['git','clone','https://github.com/CBIIT/ctdc-model'],\$in, \$out, \$err) {
    diag "cloned ctdc-model";
    chdir 'ctdc-model';
    ok( (! -e 'diff.xlsx'), 'diff.xlsx not present');
    ok run[@cmd, '--outfile','diff.xlsx'], 'run script';
    ok( (-e 'diff.xlsx'), 'diff.xlsx created');
    ok run[@cmd,'--outfile','diff2.xlsx','--skip=1','--working'], 'run with some options';
    ok( (-e 'diff2.xlsx'), 'diff2.xlsx created');
  }
  else {
    fail "Couldn't clone test repo";
  }
}

done_testing;
