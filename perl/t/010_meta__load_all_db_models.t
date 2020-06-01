use Test::More tests => 9;
use Test::Warn;
use Test::Deep;
use Test::Exception;
use IPC::Run qw/run/;
use Neo4j::Bolt;
use lib '../lib';
use Log::Log4perl qw/:easy/;
use Bento::Meta;

# --------------------
# Desc:
#   tests the Bento::Meta::load_all_db_models()
#   broke out from 009_meta.t so that db loaded models would not conflict 
#   with file loaded models (cannot load two models named ICDC)

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
  $meta = Bento::Meta->new, 'can create new Bento::Meta instance';

  # test the models found in the database
  ok my @actual_models = $meta->list_db_models("bolt://localhost:$port"), "list models from db";
  is_deeply [sort @actual_models], [qw/CTDC ICDC/], "correct handles";
  is scalar $meta->models, 0, "no models were loaded";

  # test that load_all_db_models can load 2 models: ICDC and CTDC
  ok my $model_count = $meta->load_all_db_models("bolt://localhost:$port"), "loads all models from db";
  is scalar $meta->models, 2, "meta now has expected number of models";
  isa_ok($meta->model('ICDC'), 'Bento::Meta::Model');
  isa_ok($meta->model('CTDC'), 'Bento::Meta::Model');
  ok !$meta->model('boog'), 'make sure uncreated model doesnt exist';
}
done_testing;

END {
  diag "Stopping container $ctr_name";
  run \@stopcmd;
  diag "Removing container $ctr_name";
  run \@rmcmd;
}
