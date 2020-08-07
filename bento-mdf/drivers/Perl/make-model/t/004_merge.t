use Test::More;
use Test::Exception;
use File::Spec;
use Set::Scalar;
use lib '../lib';
use Log::Log4perl::Level;
use Bento::MakeModel;
my $samplesd = File::Spec->catdir( (-d 't' ? 't' : '.'), 'samples' );
my (@n, @r);

$obj = Bento::MakeModel->new(LOG_LEVEL=>$FATAL);
$obj->read_input( File::Spec->catdir($samplesd,"icdc-model.yml"),
		  File::Spec->catdir($samplesd,"icdc-model-props.yml") );

diag "check original (before overlay)";

ok( !grep(/^experiment$/, $obj->nodes), "experiment DNE");
ok( grep(/^file$/, $obj->nodes), "file exists...");

  is $obj->get_node('file')->category, 'data_file', "...has data_file category...";
  $exp = Set::Scalar->new(qw/project_id object_id file_name file_size data_category
			   data_format data_type/);
  $got = Set::Scalar->new(map { $_->name } $obj->get_node('file')->props);
  $got->insert('fred'); # add some elt
  ok $got->is_disjoint($exp), "but no gen3 properties";
  #  ok( !grep(/^project_id$/,@{$obj->get_node('case')->root->{systemProperties}}), "case: no 'project_id' in system properties");
  ok( !grep(/^dbgap_accession_number$/,map { $_->name } $obj->get_node('program')->props), "program: no 'dbgap_accession_number' in properties");


diag "check overlay...";
$obj = Bento::MakeModel->new(LOG_LEVEL=>$FATAL);
$obj->read_input( File::Spec->catdir($samplesd,"icdc-model.yml"),
		  File::Spec->catdir($samplesd,"icdc-model-props.yml"),
		  File::Spec->catdir($samplesd,"gen3-model-overlay.yml"),
		 );
# check merge is correct - following data appear in overlay but not basic model
ok grep(/^experiment$/, $obj->nodes), "experiment present";
is $obj->get_node('image')->category, 'data_file', "set category for 'image' node correct";
ok((@a = grep { $_->{Dst} eq 'experiment' } $obj->ends('member_of')), "experiment <-member_of-... exists");

ok( (@a = grep { $_->{Src} eq 'study_arm' } $obj->ends('member_of')), "... <-member_of-study_arm exists");
$got = Set::Scalar->new(map {$_->name} $obj->get_node('file')->props);
ok $exp->is_subset($got), "file now has all properties";
# ok( grep(/^project_id$/,@{$obj->get_node('case')->root->{systemProperties}}), "case: 'project_id' now in system properties");
ok( grep(/^dbgap_accession_number$/,map { $_->name } $obj->get_node('program')->props), "program: 'dbgap_accession_number' now in properties");
done_testing;
