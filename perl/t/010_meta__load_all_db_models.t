use Test::More tests => 10;
use Test::Warn;
use Test::Deep;
use Test::Exception;
use IPC::Run qw/run/;
use Neo4j::Bolt;
use lib qw'../lib ..';
use Log::Log4perl qw/:easy/;
use Bento::Meta;

# --------------------
# Desc:
#   tests the Bento::Meta::load_all_db_models()
#   broke out from 009_meta.t so that db loaded models would not conflict 
#   with file loaded models (cannot load two models named ICDC)

Log::Log4perl->easy_init($INFO);
unless (eval 'require t::NeoCon; 1') {
  plan skip_all => "Docker not available for test database setup: skipping.";
}
my $docker = t::NeoCon->new();
$docker->start;
my $port = $docker->port(7687);

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

  # do it again without borking
  $meta = undef;
  $meta = Bento::Meta->new();
  ok $meta->load_all_db_models("bolt://localhost:$port"), "load again without bork"
}
done_testing;

END {
  $docker->stop;
  $docker->rm;
}
