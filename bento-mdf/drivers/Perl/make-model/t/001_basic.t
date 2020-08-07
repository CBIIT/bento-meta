use Test::More;
use Test::Exception;
use Log::Log4perl::Level;
use File::Spec;
use lib '../lib';
my $samplesd = File::Spec->catdir( (-d 't' ? 't' : '.'), 'samples' );
my $obj;
use_ok("Bento::MakeModel");
use_ok("Bento::MakeModel::Config");
isa_ok( $obj = Bento::MakeModel->new(), "Bento::MakeModel");
lives_ok { $obj->read_input( File::Spec->catdir($samplesd,"try.yml") ) } "read yaml";
is_deeply [sort $obj->nodes], [qw/boog goob/], "nodes";
is_deeply [sort $obj->relationships], [qw/goob_of/], "relationships";
is_deeply $obj->input->{UniversalNodeProperties}{mustHave}, ['id'], "UNP";
is_deeply $obj->input->{UniversalNodeProperties}{mayHave}, ['desc'], "UNP";
is_deeply $obj->input->{UniversalRelationshipProperties}{mustHave}, ['id'], "URP";
is_deeply $obj->input->{UniversalRelationshipProperties}{mayHave}, ['desc'], "URP";

undef $obj;
$obj = Bento::MakeModel->new(LOG_LEVEL=>$FATAL);
$obj->read_input( File::Spec->catdir($samplesd,"icdc-model.yml"), File::Spec->catdir($samplesd,"icdc-model-props.yml") );
lives_ok {@n = $obj->nodes} "nodes";
lives_ok {@r = $obj->relationships} "relationships";

# ok my $rels_of_sample = $obj->_relns_with_src_node("sample");
# is_deeply [sort keys %$rels_of_sample], [sort qw/on_visit next/], "relns of sample";


done_testing;
