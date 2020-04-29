use Test::More;
use Test::Exception;
use Log::Log4perl qw/:easy/;
use lib qw{../lib . t};
use_ok('Bento::Meta::Model::Entity');
use TestObject;
$o = TestObject->new();
Log::Log4perl->easy_init($FATAL);

# attr
is_deeply [sort $o->attrs], [sort qw/my_scalar_attr my_object_attr my_array_attr my_hash_attr desc/], "attrs()";

# setters
$value = 'narf';
is $o->set_my_scalar_attr("new value!"),'new value!', "set scalar";
ok $o->set_my_object_attr($o), "set object";
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
ok $val = TestObject->new({my_scalar_attr => 'tester'});
ok $o = TestObject->new({
  my_scalar_attr => 1,
  my_array_attr => [qw/ a b c /],
  my_hash_attr => { yet => 0, another => 1, hashref => 2},
  my_object_attr => $val,
  blarf => "fizz",
 });



is $o->my_scalar_attr, 1, "init scalar attr";
is_deeply [$o->my_array_attr], [qw/a b c/], "init array attr";
is $o->my_hash_attr('another'), 1, "init hash attr";
ok !$o->atype('my_scalar_attr'), "atype => scalar";
is $o->atype('my_object_attr'),'TestObject', "atype => object";
is $o->atype('my_array_attr'), 'ARRAY', "atype ARRAY";
is $o->atype('my_hash_attr'), 'HASH', "atype HASH";

ok $o->set_my_object_attr(undef), 'clear object attr';
ok !$o->my_object_attr, 'object cleared';
is $o->{_my_object_attr},\undef, 'cleared object is \undef';
is scalar $o->removed_entities, 1, "removed entities loaded";
is( ($o->removed_entities)[0], $val, "entity correct");
is( $o->pop_removed_entities->[1], $val, "pop rm entity");
is $o->dirty, 1;
$o->set_dirty(0);
is $o->dirty, 0;
ok !$o->neoid;
$o->set_neoid(5);
is $o->neoid, 5;
done_testing;
