use Test::More;
use Test::Warn;
use Test::Exception;
use lib '../lib';
use Bento::Meta::Model::Node;
use Bento::Meta::Model::Concept;
use Bento::Meta::Model::Property;
use strict;

use_ok('Bento::Meta::Model::ObjectMap');
throws_ok { Bento::Meta::Model::ObjectMap->new() } qr/object class/, 'check new() for arg';

ok my $map = Bento::Meta::Model::ObjectMap->new('Bento::Meta::Model::Node'), 'create object map';
isa_ok($map, 'Bento::Meta::Model::ObjectMap');

my $concept = Bento::Meta::Model::Concept->new();
$concept->set_id($concept->make_uuid);
throws_ok { $map->get_q($concept) } qr/arg1 must be an object of class/, 'get_q throws when arg has wrong class';

for my $p (qw/handle model category/) {
  ok $map->map_simple_attr($p => $p), 'map simple attr';
}
ok $map->map_object_attr('concept' => ':has_concept>',
                         'Bento::Meta::Model::Concept' => 'concept'), 'map object attr';
ok $map->map_collection_attr('props' => ':has_property>',
                             'Bento::Meta::Model::Concept' => 'property'), 'map collection attribute';

is_deeply [sort $map->property_attrs], [ sort qw/handle model category/], 'property_attrs correct';

is_deeply [sort $map->relationship_attrs], [ sort qw/concept props/ ], 'relationship_attrs correct';

ok my $node = Bento::Meta::Model::Node->new({
  handle => 'test',
  model => 'test_model',
});

ok my $find_q = $map->get_q($node);
like $find_q->as_string, qr/category IS NULL/;
like $find_q->as_string, qr/handle = 'test'/;
like $find_q->as_string, qr/model = 'test_model'/, "find query correct";

$node->set_neoid(1);
ok my $exact_q = $map->get_q($node);
is $exact_q->as_string, "MATCH (n:node) WHERE (id(n) = 1) RETURN n,id(n)", "exact query correct";

throws_ok { $map->get_attr_q($node, 'frelb') } qr/not a registered attr/, "throw on unknown attr";

ok my $simple_q = $map->get_attr_q($node, 'handle'), "simple attr";
ok my $object_q = $map->get_attr_q($node, 'concept'), "object attr";
ok my $collect_q = $map->get_attr_q($node, 'props') , "collection attr";

$node->set_neoid(undef);
my $put_q = $map->put_q($node);
ok( ($put_q->as_string eq "CREATE (n:node {handle:'test',model:'test_model'}) RETURN id(n)") or ($put_q->as_string eq  "CREATE (n:node {model:'test_model',handle:'test'}) RETURN id(n)"), "put (new node) correct");
$node->set_neoid(1);
my @upd_q = $map->put_q($node);
is scalar @upd_q, 2, "two put (existing node) queries";
ok( ($upd_q[0]->as_string eq "MATCH (n:node) WHERE (id(n) = 1) SET handle = 'test',model = 'test_model' RETURN id(n)") or ($upd_q[0]->as_string eq "MATCH (n:node) WHERE (id(n) = 1) SET model = 'test_model',handle = 'test' RETURN id(n)"), "set props query correct");
is $upd_q[1]->as_string, "MATCH (n:node) WHERE (id(n) = 1) REMOVE n.category RETURN id(n)", "rm props query correct";

$node->set_neoid(undef);
throws_ok { $map->put_attr_q($node) } qr/must be a mapped object/, "throw if obj not mapped";
$node->set_neoid(1);
throws_ok { $map->put_attr_q($node,'concept' => $concept) } qr/must all be mapped objects/, "throw if value not mapped";
$concept->set_neoid(2);
throws_ok {  $map->put_attr_q($node,'concept' => 'boog') } qr/must all be Entity objects/, "throw if not all values are objects";

$concept->neoid(2);
my ($put_obj_q) = $map->put_attr_q($node,'concept' => $concept), 'put_attr_q(obj)';

like $put_obj_q->as_string, qr"MATCH \(n:node\),\(a:concept\) WHERE \(\(id\([na]\) = [12]\) AND \(id\([na]\) = [12]\)\) MERGE \(n\)-\[:has_concept\]->\(a\) RETURN id\(a\)", "put obj attribute query correct";

my @props;
for (5..10) {
  my $p = Bento::Meta::Model::Property->new({handle=>"prop$_", model =>'test', value_domain => "string"});
  $p->set_neoid($_);
  push @props, $p;
}
my @put_coll_q = $map->put_attr_q($node,'props' => @props),'put_attr_q(collection)';
is scalar @put_coll_q, 6, 'correct number of queries';
like $put_coll_q[0]->as_string, qr"MATCH \(n:node\),\(a:property\) WHERE \(\(id\([na]\) = [15]\) AND \(id\([na]\) = [15]\)\) MERGE \(n\)-\[:has_property\]->\(a\) RETURN id\(a\)", 'query correct';

ok my $rm_q = $map->rm_q($node), "rm_q(obj)";
is $rm_q->as_string, "MATCH (n:node) WHERE (id(n) = 1) DELETE n RETURN id(n)", 'query correct';

ok my @rm_attr_q = $map->rm_attr_q($node, 'concept' => $concept), 'rm_attr_q object prop';
like $rm_attr_q[0]->as_string, qr"MATCH \(n:node\)-\[r:has_concept\]->\(v:concept\) WHERE \(\(id\([nv]\) = [12]\) AND \(id\([nv]\) = [12]\)\) DELETE r RETURN id\(v\)", 'query correct';
ok my @rm_attr_q = $map->rm_attr_q($node, props => ':all'), 'rm_attr_q collection prop/:all';
is scalar @rm_attr_q, 1;
is $rm_attr_q[0]->as_string, "MATCH (n:node)-[r:has_property]->(v:property) WHERE (id(n) = 1) DELETE r RETURN id(v)", 'query correct';
ok @rm_attr_q = $map->rm_attr_q($node, props => @props), 'rm_attr_q object props/each';
is scalar @rm_attr_q, 6; 
like $rm_attr_q[0]->as_string, qr"MATCH \(n:node\)-\[r:has_property\]->\(v:property\) WHERE \(\(id\([nv]\) = [15]\) AND \(id\([nv]\) = [15]\)\) DELETE r RETURN id\(v\)", 'query correct';

# adding object map methods to class
ok !$Bento::Meta::Model::Node::OBJECT_MAP;
ok "Bento::Meta::Model::Node"->object_map(
  {
    simple => [
      [model => 'model'],
      [handle => 'handle']
     ],
    object => [
      [ 'concept' => '<:has_concept',
        'Bento::Meta::Model::Concept' => 'concept' ],
     ],
    collection => [
      [ 'props' => '<:has_property',
        'Bento::Meta::Model::Property' => 'property' ],
     ]
    }
 );
isa_ok $Bento::Meta::Model::Node::OBJECT_MAP, 'Bento::Meta::Model::ObjectMap';
can_ok($node,'get');

done_testing;
