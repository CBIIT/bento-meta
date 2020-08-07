use Test::More;
use Test::Exception;
use lib '../lib';
use File::Spec;
use Try::Tiny;
use JSON;
use IPC::Run qw/run/;

my $dir = (-d 't' ? '.' : '..');
my @testoutf = qw/try.svg try.json try.txt/;
my $sampdir = File::Spec->catdir($dir, qw/t samples/);
my $tool = File::Spec->catfile($dir, 'bin', 'model-tool-d');

ok( (-x $tool), "Found model-tool-d");

SKIP : {
  my ($in, $out, $err);
  skip "Docker not available: skipping.", 1 unless run(['docker'],'<pty<',\$in,'>pty>',\$out);
  my @cmd = ($tool);
  my @descfiles = map { File::Spec->catfile($sampdir,$_) } qw/icdc-model.yml icdc-model-props.yml/;

  lives_ok { run(\@cmd, '<pty<', \$in, '>pty>', \$out) } "It runs";
  like ($out, qr/FATAL: Nothing to do!/, "Emit 'Nothing to do'");
  like ($out, qr/Usage:.*model-tool.*--dry-run/s, "Emit usage hints");

  push @cmd, '--dry-run';

  lives_ok { run([@cmd,@descfiles], '<pty<', \$in, '>pty>', \$out) } "Dry run";
  unlike ($out, qr/FATAL|ERROR/, "No errors thrown");


  try {
    unlink map {File::Spec->catfile($dir, $_)} @testoutf;
  } catch {
    1;
  };

  $in = $out = $err = '';

  lives_ok { run( [$tool, '-g', '-v', File::Spec->catfile($dir,'try.svg'), @descfiles],
                  '<pty<', \$in, '>pty>', \$out) } "-g -v [file] (bad option order)" ;
  like ($out, qr/FATAL.*requires an arg/s, "Got correct error");

  $in = $out = $err = '';

  lives_ok { run( [$tool, '-g', File::Spec->catfile($dir,'try.svg'),'-T','-v', @descfiles],
                  '<pty<', \$in, '>pty>', \$out) } "-g [file] -s -v (bad option order)" ;
  like ($out, qr/FATAL.*requires an arg/s, "Got correct error");

  $in = $out = $err = '';
  lives_ok { run( [$tool, '-g', File::Spec->catfile($dir,'try.svg'), @descfiles],
                  '<pty<', \$in, '>pty>', \$out) } "-g";
  diag $out if $out;
  ok(( -e File::Spec->catfile($dir,'try.svg')), "svg created");

  $in = $out = $err = '';
  lives_ok { run( [$tool, '-T', File::Spec->catfile($dir,'try.txt'), @descfiles],
                  '<pty<', \$in, '>pty>', \$out) } "-T";
  diag $out if $out;
  ok(( -e File::Spec->catfile($dir,'try.txt')), "txt created");

  try {
    unlink File::Spec->catfile($dir, 'try.txt');
  } catch {
    1;
  };


  lives_ok { run( [$tool, '-T', File::Spec->catfile($dir,'try.txt'), '--dry-run', @descfiles],
                  '<pty<', \$in, '>pty>', \$out) } "-T --dry-run";

  ok(( ! -e File::Spec->catfile($dir,'try.txt')), "txt not created in dry run");
}

done_testing;

END {
  try {
  unlink map {File::Spec->catfile($dir, $_)} @testoutf;
} catch {
  1;
};
}
