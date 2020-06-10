use Test::More;
use Test::Warn;
use Test::Exception;
use IPC::Run qw/run/;
use Neo4j::Bolt;
use lib qw{../lib ..};
use Log::Log4perl qw/:easy/;
use Bento::Meta::Model::ObjectMap;
use Bento::Meta::Model::Node;
use Bento::Meta::Model::ValueSet;
use Bento::Meta::Model::Term;

Log::Log4perl->easy_init($INFO);
####
unless (eval 'require t::NeoCon; 1') {
  plan skip_all => "Docker not available for test database setup: skipping.";
}
my $docker = t::NeoCon->new();
$docker->start;
my $port = $docker->port(7687);
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

  diag "test get()";
  ok $res = $cxn->run_query('match (a:node) return id(a) limit 1 ');
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

    
  diag "test put()";
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
  
  diag "test rm()";
  ok my $rm_term = $vset->set_terms(quilm => undef), 'delete term from value_set object';
  @terms = $vset->terms;
  is scalar @terms, 2, "deleted";
  warning_like { $rm_term->rm } qr/server error: Cannot delete/, "warn - try to rm, but reln still present";
  ok $res = $cxn->run_query( "match (t:term {value:'quilm'}) return id(t)" );
  ok my ($t_id) = $res->fetch_next;
  is $rm_term->neoid, $t_id, "term still in db";
  ok $rm_term->rm(1), "force rm";
  ok $res = $cxn->run_query( "match (t:term {value:'quilm'}) return id(t)" );
  ok !$res->fetch_next, "now term gone from db";

  diag "test add(), drop()";
  ok my $new_term = Bento::Meta::Model::Term->new({ value => 'belpit' }), 'make new term';
  ok $new_term->put, 'put into db';
  ok $vset->add('terms', $new_term), "connect term to vset in db";
  @terms = $vset->terms;
  is scalar @terms, 2, "vset obj still has just 2 terms";
  ok $vset->get(1), "now get() vset from db";
  @terms = $vset->terms;
  is scalar @terms, 3, "now vset has 3 terms";
  ok $vset->terms('belpit'), "there it is";

  ok my $old_term = $vset->terms('ferb'), "get existing term";
  ok $res = $cxn->run_query("match (t:term {value:'ferb'})<-[r]-(v:value_set) return r"), "find reln in db";
  ok my ($r) = $res->fetch_next;
  isa_ok($r, 'Neo4j::Bolt::Relationship');
  ok $vset->drop('terms', $old_term), "disconnect it";
  ok $res = $cxn->run_query("match (t:term {value:'ferb'})<-[r]-(v:value_set) return r"), "try to find reln in db";
  ok !$res->fetch_next, "it's gone";
  ok $res = $cxn->run_query("match (t:term {value:'ferb'}) return t"), "try to find term in db";
  ok (($r) = $res->fetch_next, "it's still there");
  isa_ok($r, 'Neo4j::Bolt::Node');
  @terms = $vset->terms;
  is scalar @terms, 3, "vset still has 3 terms";
  ok $vset->get(1), "get() vset, force refressh";
  @terms = $vset->terms;
  is scalar @terms, 2, "vset now has 2 terms";
  is_deeply [ sort map {$_->value} @terms ], [ qw/belpit narquit/ ], "and they're the right ones";

  ok $old_term = $vset->set_terms('belpit' => undef), "delete another term on object";
  ok $vset->drop_terms($old_term), "now use drop_terms to remove link in db";
  ok $vset->get(1), "update from db (force refresh)";
  @terms = $vset->terms;
  is scalar @terms, 1, 'only one term left';
  $new_term = Bento::Meta::Model::Term->new({value => 'goob'});
  ok $vset->set_terms('goob' => $new_term);
  ok $new_term->put;
  ok $vset->add_terms($new_term);
  ok $vset->get(1), "force refresh";
  @terms = $vset->terms;
  is scalar @terms, 2, 'add_terms added a term';
  
  
  
}

done_testing;

END {
  $docker->stop;
  $docker->rm;
}
