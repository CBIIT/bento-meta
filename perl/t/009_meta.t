use Test::More;
use Test::Warn;
use Test::Exception;
use IPC::Run qw/run/;
use Neo4j::Bolt;
use lib '../lib';
use Log::Log4perl qw/:easy/;
use Bento::Meta;

Log::Log4perl->easy_init($FATAL);
my $ctr_name = "test$$";
my $img = 'maj1/test-db-bento-meta';
my $d = (-e 't' ? 't' : '.');

####
diag "Starting docker container '$ctr_name' with image $img";
my @startcmd = split / /,
  "docker run -d -P --name $ctr_name $img";
my @portcmd = split / /, "docker container port $ctr_name";
my @stopcmd = split / /,"docker kill $ctr_name";
my @rmcmd = split / /, "docker rm $ctr_name";

my ($in, $out, $err);
unless (run(['docker'],'<pty<',\$in,'>pty>',\$out)) {
  plan skip_all => "Docker not available for test database setup: skipping.";
}
run \@startcmd, \$in, \$out, \$err;
if ($err) {
  diag "docker error: $err";
}
else {
  sleep 10;
}
$in=$err=$out='';
run \@portcmd, \$in, \$out, \$err;
my ($port) = grep /7687.tcp/, split /\n/,$out;
($port) = $port =~ m/([0-9]+)$/;
####
ok my $cxn = Neo4j::Bolt->connect("bolt://localhost:$port"), 'create neo4j connection';
SKIP : {
  skip "Can't connect to test db: ".$cxn->errmsg, 1 unless $cxn->connected;
  ok my $meta = Bento::Meta->new;
  isa_ok($meta, 'Bento::Meta');
  ok my $mdfm = $meta->load_model( 'ICDC', File::Spec->
  catfile($d,'samples','icdc-model.yml'), File::Spec->
  catfile($d,'samples','icdc-model-props.yml')), "load model from MDF";
  isa_ok($mdfm, 'Bento::Meta::Model');
  ok my $neom = $meta->load_model( 'CTDC', "bolt://localhost:$port"), "load model from db";
  isa_ok($neom, 'Bento::Meta::Model');
  is scalar $meta->models, 2, "two models";
  is_deeply [sort $meta->handles], [qw/CTDC ICDC/], "correct handles";
  isa_ok($meta->model('ICDC'), 'Bento::Meta::Model');
  isa_ok($meta->model('CTDC'), 'Bento::Meta::Model');
  ok !$meta->model('boog');
}
done_testing;

END {
  diag "Stopping container $ctr_name";
  run \@stopcmd;
  diag "Removing container $ctr_name";  
  run \@rmcmd;
}
