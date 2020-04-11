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

for my $p (qw/handle model category/) {
  ok $map->map_simple_attr($p => $p), 'map simple attr';
}
ok $map->map_object_attr('concept' => 'has_concept', 'concept'), 'map object attr';
ok $map->map_collection_attr('props' => 'has_property', 'property'), 'map collection attribute';

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
is $exact_q->as_string, "MATCH (n:node) WHERE (id(n) = 1) RETURN n", "exact query correct";

throws_ok { $map->get_attr_q($node, 'frelb') } qr/not a registered attr/, "throw on unknown attr";

ok my $simple_q = $map->get_attr_q($node, 'handle'), "simple attr";
ok my $object_q = $map->get_attr_q($node, 'concept'), "object attr";
ok my $collect_q = $map->get_attr_q($node, 'props') , "collection attr";

$DB::single=1;
done_testing;
