use Test::More;
use Test::Warn;
use Test::Exception;
use IPC::Run qw/run/;
use Neo4j::Bolt;
use lib '../lib';
use Bento::Meta::Model::ObjectMap;
use Bento::Meta::Model::Node;
use Bento::Meta::Model::ValueSet;
use Bento::Meta::Model::Term;

my $ctr_name = "test$$";
my $img = 'maj1/test-db-bento-meta';

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
sleep 10;
$in=$err=$out='';
run \@portcmd, \$in, \$out, \$err;
my ($port) = grep /7687.tcp/, split /\n/,$out;
($port) = $port =~ m/([0-9]+)$/;
####
ok my $cxn = Neo4j::Bolt->connect("bolt://localhost:$port"), 'create neo4j connection';
SKIP : {
  skip "Can't connect to test db: ".$cxn->errmsg, 1 unless $cxn->connected;
  ok my $omap = "Bento::Meta::Model::Node"->object_map(
    {
      simple => [
        [model => 'model'],
        [handle => 'handle']
       ],
      object => [
        [ 'concept' => ':has_concept>',
          'Bento::Meta::Model::Concept' => 'concept' ],
       ],
      collection => [
        [ 'props' => ':has_property>',
          'Bento::Meta::Model::Property' => 'property' ],
       ]
     }
   ), "create ObjectMap for Node class";

  ok $omap->bolt_cxn($cxn), 'set db connection';
  isa_ok $Bento::Meta::Model::Node::OBJECT_MAP,'Bento::Meta::Model::ObjectMap';
  my $res;
  is $omap, $Bento::Meta::Model::Node::OBJECT_MAP, "pointer same";
  ok $res = $cxn->run_query('match (a:node) return id(a) limit 1');
  ok my ($n_id) = $res->fetch_next;
  my $node = Bento::Meta::Model::Node->new();
  $node->set_neoid($n_id);
  ok $node->get(), "get node with neoid $n_id";
  is $node->dirty, 0, "node clean";
  is $node->concept->dirty, -1, "object property dirty with -1";
  is $node->concept->id, "a5b87a02-1eb3-4ec9-881d-f4479ab917ac", "concept id correct";
  my @p = $node->props;
  is scalar @p, 3, "has 3 properties";
  is $node->props('site_short_name')->dirty, -1, "prop dirty with -1";
  is $node->props('site_short_name')->model, "ICDC", "attr of prop";

  ok "Bento::Meta::Model::ValueSet"->object_map(
    {
      label => 'value_set',
      simple => [
        [id => 'id'],
        [handle => 'handle'],
        [url => 'url'],
       ],
      object => [
       ],
      collection => [
        [ 'terms' => ':has_term>',
          'Bento::Meta::Model::Term' => 'term' ],
       ]
     }
  )
    ->bolt_cxn($cxn), "create ObjectMap for ValueSet class";
  ok "Bento::Meta::Model::Term"->object_map(
   {
      simple => [
        [id => 'id'],
        [value => 'value'],
        [origin_id => 'origin_id'],
        [origin_definition => 'origin_definition']        
       ],
      object => [
        [ 'concept' => ':has_concept>',
          'Bento::Meta::Model::Concept' => 'concept' ],
       ],
      collection => [
       ]
     }
  )
    ->bolt_cxn($cxn), "create ObjectMap for Term class";
  ok my $vset = Bento::Meta::Model::ValueSet->new({ id => "narb" }), "a valueset";
  my %terms;
  for (qw/ quilm ferb narquit /) {
    $terms{$_} = Bento::Meta::Model::Term->new({ value => $_ });
  }
  $vset->set_terms(\%terms);
  is $vset->terms('quilm')->value, 'quilm', "a term";
  $DB::single=1;
  $vset->put;
  ok $vset->neoid, "vset neoid set";
  for (values %terms) {
    ok $_->neoid, "term neoid set";
  }
  ok $res = $cxn->run_query( "match (v:value_set) where v.id = 'narb' return v");
  my ($v_db) = $res->fetch_next;
  is $v_db->{properties}{id}, 'narb', 'vset in the db';
  ok $res = $cxn->run_query( "match (v:value_set)-[:has_term]->(t:term) where v.id = 'narb' return t order by t.value");
  my @terms;
  while (my ($t) = $res->fetch_next) {
    push @terms, $t->{properties}{value};
  }
  is_deeply [sort @terms], [sort qw/ quilm ferb narquit /], 'terms in db';
  
}

done_testing;

END {
  diag "Stopping container $ctr_name";
  run \@stopcmd;
  diag "Removing container $ctr_name";  
  run \@rmcmd;
}
