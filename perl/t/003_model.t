use Test::More;
use Test::Exception;
use lib '../lib';

use_ok('Bento::Meta::Model');

ok $model = Bento::Meta::Model->new('test'), 'create model';
isa_ok($model, 'Bento::Meta::Model');



done_testing;
