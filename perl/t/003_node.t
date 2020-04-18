use Test::More;
use Test::Exception;
use lib '../lib';

use_ok('Bento::Meta::Model::Node');

ok $node = Bento::Meta::Model::Node->new(), 'create Node';
isa_ok($node, 'Bento::Meta::Model::Node');
isa_ok($node, 'Bento::Meta::Model::Entity');

is_deeply [ sort @{$node->{_declared}}],
  [sort qw/handle model concept tags category props desc /], 'declared attrs correct';

lives_ok { $node->handle; };
dies_ok { $node->boog; };

  
  

done_testing;
