use Test::More;
use Test::Exception;
use Log::Log4perl qw/:easy/;
use lib qw{../lib . t};
use_ok('Bento::Meta::Model::Entity');
use TestObject;
$o = TestObject->new();
Log::Log4perl->easy_init($DEBUG);

# attr
is_deeply [sort $o->attrs], [sort qw/my_scalar_attr my_array_attr my_hash_attr dirty desc neoid/], "attrs()";

# setters
$value = 'narf';
is $o->set_my_scalar_attr("new value!"),'new value!', "set scalar";
is_deeply [ sort @{$o->set_my_array_attr( [ qw/ arrayref with some values / ] )}], [sort qw/ arrayref with some values/ ], "replace arrayref";
is $o->set_my_hash_attr( key => $value ), 'narf', "set a value for a key in hash attr";
is_deeply $o->set_my_hash_attr( { brand => 1, new => 2, hashref => 3 }),{ brand => 1, new => 2, hashref => 3 }, "replace hashref";
# getters
is $o->my_scalar_attr,'new value!',  "get scalar value";
is_deeply [$o->my_array_attr],[ qw/ arrayref with some values / ],"get array, not ref";
my $h = $o->my_hash_attr;
is_deeply $h, { brand => 1, new => 2, hashref => 3 }, "get hashref";
is_deeply [sort ($o->my_hash_attr)], [1,2,3], "get hash values";
is $o->my_hash_attr('brand'), 1, "get hash value for key";

# init
ok $o = TestObject->new({
  my_scalar_attr => 1,
  my_array_attr => [qw/ a b c /],
  my_hash_attr => { yet => 0, another => 1, hashref => 2},
  blarf => "fizz",
 });

is $o->my_scalar_attr, 1, "init scalar attr";
is_deeply [$o->my_array_attr], [qw/a b c/], "init array attr";
is $o->my_hash_attr('another'), 1, "init hash attr";

done_testing;
