use Test::More;
use Test::Warn;
use Test::Exception;
use IPC::Run qw/run/;
use Neo4j::Bolt;
use lib qw'../lib ..';
use Log::Log4perl qw/:easy/;
use Bento::Meta::Model;

Log::Log4perl->easy_init($INFO);
unless (eval 'require t::NeoCon; 1') {
  plan skip_all => "Docker not available for test database setup: skipping.";
}
my $docker = t::NeoCon->new;
$docker->start;
my $port = $docker->port(7687);

ok my $cxn = Neo4j::Bolt->connect("bolt://localhost:$port"), 'create neo4j connection';
SKIP : {
  skip "Can't connect to test db: ".$cxn->errmsg, 1 unless $cxn->connected;

  ok my $model = Bento::Meta::Model->new('ICDC', $cxn), "create Model obj with Neo4j mapping";
  diag "get model from db";
#  ok $model->get, "load model from db";

  ok my ($dbc) = $cxn->run_query('match (n:node) where n.model="ICDC" return count(n)')
    ->fetch_next,"fetch no. db nodes";
  is scalar $model->nodes, $dbc, 'number of nodes correct';

  ok my ($dbc) = $cxn->run_query('match (n:relationship) where n.model="ICDC" return count(n)')
    ->fetch_next, "fetch no. db edges";
  is scalar $model->edges, $dbc, 'number of edges correct';

  ok my ($dbc) = $cxn->run_query('match (n:node)-->(p:property) where n.model="ICDC" return count(p)')
    ->fetch_next,"fetch no. db props";
  is scalar $model->props, $dbc, 'number of props correct';

  ok my $res = $cxn->run_query(<<QRY);
    match (s:node)<-[:has_src]-(e:relationship)-[:has_dst]->(d:node)
    where (e.model = 'ICDC')
    return s,e,d
QRY
  while (my ($s,$e,$d) = $res->fetch_next) {
    my $triplet = join(':',$e->{properties}{handle},
                       $s->{properties}{handle},
                       $d->{properties}{handle});
    is $model->edge($triplet)->src->handle, $s->{properties}{handle}, "edge $triplet src";
    is $model->edge($triplet)->dst->handle, $d->{properties}{handle}, "edge $triplet dst";
  }
  
  ok $res = $cxn->run_query(<<QRY);
    match (n:node)-[:has_property]->(p:property)
    where (n.model = 'ICDC')
    return n, collect(p);
QRY
  while (my ($n, $pp) = $res->fetch_next) {
    for my $p (@$pp) {
      my $k = join(':',$$n{properties}{handle},$$p{properties}{handle});
      ok my $mp = $model->prop($k), "property $k in model";
      if ($mp) {
        is $mp->neoid,
          ,$$p{id},"property '$$p{properties}{handle}' in model props";
        is $model->node($n->{properties}{handle})->props($p->{properties}{handle})->neoid, $p->{id}, "model has property '$$p{properties}{handle}' for node '$$n{properties}{handle}'";
      }
    }
  }

  # test whether value sets are present in model
  # test checks terms() on property object, auto-get of partial object (vs)
  ok $res = $cxn->run_query(<<QRY);
    match (t:term)<-[:has_term]-(v:value_set)<-[:has_value_set]->(p:property)
    where (p.model = 'ICDC')
    return p, v, collect(t);
QRY
  while (my ($p,$v, $t) = $res->fetch_next) {
    my ($op) = grep {$_->handle eq $p->{properties}{handle}} ($model->props);
    ok $op, "have property '$$p{properties}{handle}'";
    is_deeply [ sort map {$_->value} $op->terms ],
      [ sort map {$_->{properties}{value}} @$t ], 'all terms present on object';
  }

  # test pushing model (updates) to db

  # types of changes:
  # change obj simple attr -> db node property changed *
  # unset (undef) obj simple attr -> db node prop removed *
  # set previously undef simple attr -> db node prop created and set 
  # delete obj from obj collection attr -> db relationship between src and dst removed 
  # add obj to obj collection attr -> db relationship (and dst node) created, others unchanged *
  # unset obj object attr - db relationship removed *
  # change obj object attr - db relationship removed from original dst, new relationship (and dst node) created *
  # object removed from model - db node and attached relationships deleted (or just relationships? Yes - "soft delete") 
  # term / valueset

  # put() any dirty object contained by the model (node, relationship, property)
  # - this will include new unmapped objects which are dirty by default
  # 
  # What else needs to be 'put'? Any object that has been created in the object
  # model, but is not yet represented in the db (i.e., has no neoid)
  # for nodes, edges, props - these can be obtained directly from the 
  # model object
  # what about terms, valuesets, concepts? -- these can be shared among models
  # in the metadb, for example.

  diag "put model to db";

  ok my $prop = $model->prop('sample:sample_type'), "get existing property";

  ok $model->put, "try put (no changes, just run it)";

  ok my $sample = $model->node('sample'), "get existing node";
  ok my $edge = $model->edge('on_visit:sample:visit'), "get existing edge";

  is $prop->dirty, 0, "prop clean";

  ok my $t = Bento::Meta::Model::Term->new({value => "electric_boogaloo"}), "create new term";
  is $t->dirty, 1, "new term dirty";

  ok $model->add_terms($prop => $t), "add term to property";
  is $prop->dirty, 1, "prop dirty";
  is $prop->value_set->dirty, 1, "value set dirty";

  
  ok my $node = $model->node('lab_exam'), "get existing otherx node";
  ok $node->set_model("boog"), "change model property";
  is $node->model, "boog", "prop set in object";
  ok $model->put, "put changes";
  ok $res = $cxn->run_query(<<QRY);
  match (v:value_set)-->(t:term {value:"electric_boogaloo"})
  return v, t
QRY
  ok my ($v, $m) = $res->fetch_next, "retrieved value set and new term";
  is $v->{id}, $prop->value_set->neoid, "correct value set";
  is $m->{id}, $t->neoid, "correct property";
  is $m->{properties}{value},$t->value, "prop handle correct";
  ok $res = $cxn->run_query(<<QRY);
  match (n:node {handle:"lab_exam",model:"boog"}) return n
QRY

  ok my ($n) = $res->fetch_next, "retrieved node with changed model property";
  is $n->{id}, $node->neoid, "correct node changed";

  ok my $term = $model->prop('demographic:sex')->terms('M'), "get existing term";
  ok $term->concept, "it represents a concept";
  is $term->concept->id, "337c0e4f-506a-4f4e-95f6-07c3462b81ff", "correct concept";
  ok my $concept = $term->set_concept(undef), "remove concept";
  ok $res = $cxn->run_query(<<'QRY', { id => $term->neoid });
  match (t:term) where id(t) = $id return t
QRY
  ok my ($got_t) = $res->fetch_next, "got term";
  ok $res = $cxn->run_query(<<'QRY', { id => $term->id });
  match (t:term)-->(c:concept) where id(t) = $id return t
QRY
  ok !$res->fetch_next, "link to concept gone";
  ok $res = $cxn->run_query(<<'QRY', { id => $concept->id });
  match (c:concept) where c.id = $id return c
QRY
  ok my ($got_c) = $res->fetch_next, "but concept node still there";

  ok $concept->set_id("heydude"), "set concept id attr";
  ok $term->set_concept($concept), "set term concept back";

  ok $prop->set_model(undef), "undef simple attribute";
  ok !$prop->model, "undeffed";

  ok $model->put, "put model";

  ok $res = $cxn->run_query(<<'QRY', { id => $term->neoid });
  match (t:term)--(c:concept) where id(t) = $id return c
QRY
  ok (($got_c) = $res->fetch_next, "got concept via relnship");
  is $got_c->{id}, $concept->neoid, "the old concept";
  is $got_c->{properties}{id}, "heydude", "the new id";
  ok $res = $cxn->run_query(<<'QRY', { id => $prop->neoid });
  match (p:property) where id(p) = $id return p
QRY
  ok my ($got_prop) = $res->fetch_next;
  is $got_prop->{id}, $prop->neoid, "the old prop";
  ok !$got_prop->{properties}{model}, "but model attr is gone";
  ####
  ok $prop->set_model('ICDC'), "set model back on prop";
  
  ok my $at_enrollment = $model->edges('at_enrollment:prior_surgery:enrollment'),
    "get edge";
  ok my $prior_surgery = $model->nodes('prior_surgery'), "got node prior_surgery";
  ok $res = $cxn->run_query(<<'QRY', { id => $prior_surgery->neoid });
  match (n:node)<-[:has_src]-(r:relationship {handle:'at_enrollment'})
        -[:has_dst]->(:node {handle:'enrollment'})
  where id(n) = $id return r;
QRY
  ok my ($got_edge) = $res->fetch_next, "edge connected in db";
  ok $at_enrollment = $model->rm_edge($at_enrollment), "rm edge from model";
  is $at_enrollment->dirty, 1, "edge now dirty";
  ok !$at_enrollment->src, "no src";
  ok !$at_enrollment->dst, "no dst";
  ok( !(grep { $_->handle eq 'at_enrollment' } $model->edges_out($prior_surgery)), "prior_surgery no longer has edge in model");

  ok $model->put, "put model";
  is $at_enrollment->dirty, 0, "at_enrollment now clean";
  ok $res = $cxn->run_query(<<'QRY', { id => $prop->neoid });
  match (p:property) where id(p) = $id return p
QRY
  ok( ($got_prop) = $res->fetch_next, "got prop");
  is $got_prop->{properties}{model}, "ICDC", "model added back and set";
  ok $res = $cxn->run_query(<<'QRY', { id => $prior_surgery->neoid });
  match (n:node)<-[:has_src]-(r:relationship {handle:'at_enrollment'})
        -[:has_dst]->(:node {handle:'enrollment'})
  where id(n) = $id return r;
QRY
  ok !$res->fetch_next, "edge now not connected in db";

  ok $res = $cxn->run_query(<<'QRY', { id => $at_enrollment->neoid });
  match (e:relationship) where id(e) = $id return e;
QRY
  ok (($got_edge) = $res->fetch_next, "but relationship node still in db");
  
  1;
}

done_testing;

END {
  $docker->stop;
  $docker->rm;
}
