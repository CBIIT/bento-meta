use Test::More;
use Test::Exception;
use lib '../lib';

use_ok('Bento::Meta::Model::Node');

ok $node = Bento::Meta::Model::Node->new(), 'create Node';
isa_ok($node, 'Bento::Meta::Model::Node');
isa_ok($node, 'Bento::Meta::Model::Entity');

is_deeply [ sort @{$node->{_declared}}],
  [sort qw/handle model concept tags category props id desc /], 'declared attrs correct';

lives_ok { $node->handle; };
dies_ok { $node->boog; };

is $node->set_model('CTDC'),'CTDC', "set_model";
is $node->model,'CTDC',"set correct";
my $neonode =  {
  'id' => 4383,
  'labels' => ['property'],
   'properties' => {
      'handle' => 'registering_institution',
      'value_domain' => 'string'
     }
  };
bless $neonode, 'Neo4j::Bolt::Node';
ok $node->set_with_node($neonode), "set_with_node";
is $node->handle, 'registering_institution';
ok !$node->model, 'model undef';

ok $node->set_id("blarg");
is $node->id, "blarg";

done_testing;
