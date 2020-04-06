use Test::More;
use Test::Exception;
use lib '../lib';

use_ok('Bento::Meta::Model::Model');

ok $model = Bento::Meta::Model::Model->new('test'), 'create model';
isa_ok($model, 'Bento::Meta::Model::Model');



done_testing;
