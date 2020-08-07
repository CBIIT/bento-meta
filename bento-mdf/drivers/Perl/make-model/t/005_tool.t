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
my $tool = File::Spec->catfile($dir, 'bin', 'model-tool');

ok( (-x $tool), "Found model-tool");

my @cmd = ($^X, $tool);
my @descfiles = map { File::Spec->catfile($sampdir,$_) } qw/icdc-model.yml icdc-model-props.yml/;
my ($in, $out, $err);

lives_ok { run(\@cmd, \$in, \$out, \$err) } "It runs";
like ($err, qr/FATAL: Nothing to do!/, "Emit 'Nothing to do'");
like ($err, qr/Usage:.*model-tool.*--dry-run/s, "Emit usage hints");

push @cmd, '--dry-run';

lives_ok { run([@cmd,@descfiles], \$in, \$out, \$err) } "Dry run";
unlike ($err, qr/FATAL|ERROR/, "No errors thrown");


try {
  unlink map {File::Spec->catfile($dir, $_)} @testoutf;
} catch {
  1;
};

$in = $out = $err = '';

lives_ok { run( [$^X, $tool, '-g', '-v', File::Spec->catfile($dir,'try.svg'), @descfiles],
		\$in, \$out,\$err) } "-g -v [file] (bad option order)" ;
like ($err, qr/FATAL.*requires an arg/s, "Got correct error");

$in = $out = $err = '';

lives_ok { run( [$^X, $tool, '-g', File::Spec->catfile($dir,'try.svg'),'-T','-v', @descfiles],
		\$in, \$out,\$err) } "-g [file] -s -v (bad option order)" ;
like ($err, qr/FATAL.*requires an arg/s, "Got correct error");

$in = $out = $err = '';
lives_ok { run( [$^X, $tool, '-g', File::Spec->catfile($dir,'try.svg'), @descfiles],
		\$in, \$out, \$err ) } "-g";
diag $out if $out;
diag $err if $err;
ok(( -e File::Spec->catfile($dir,'try.svg')), "svg created");

$in = $out = $err = '';
lives_ok { run( [$^X, $tool, '-T', File::Spec->catfile($dir,'try.txt'), @descfiles],
		\$in, \$out, \$err ) } "-T";
diag $err if $err;
ok(( -e File::Spec->catfile($dir,'try.txt')), "txt created");

try {
  unlink File::Spec->catfile($dir, 'try.txt');
} catch {
  1;
};


lives_ok { run( [$^X, $tool, '-T', File::Spec->catfile($dir,'try.txt'), '--dry-run', @descfiles],
		\$in, \$out, \$err ) } "-T --dry-run";

ok(( ! -e File::Spec->catfile($dir,'try.txt')), "txt not created in dry run");


1;

done_testing;

END {
  try {
  unlink map {File::Spec->catfile($dir, $_)} @testoutf;
} catch {
  1;
};
}
