use Test::More;
use Test::Warn;
use Test::Exception;
use IPC::Run qw/run/;
use Neo4j::Bolt;
use lib qw'../lib ..';
use Log::Log4perl qw/:easy/;
use Bento::Meta;

Log::Log4perl->easy_init($INFO);
my $d = (-e 't' ? 't' : '.');

unless (eval 'require t::NeoCon; 1') {
  plan skip_all => "Docker not available for test database setup: skipping.";
}
my $docker = t::NeoCon->new;
$docker->start;
my $port = $docker->port(7687);


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
  $docker->stop;
  $docker->rm;
}
