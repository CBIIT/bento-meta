use Test::More;
use Test::Exception;
use YAML::PP qw/LoadFile/;
use File::Spec;
use Set::Scalar;
use lib '../lib';
use Log::Log4perl::Level;
use Bento::MakeModel;
use Tie::IxHash;

my $samplesd = File::Spec->catdir( (-d 't' ? 't' : '.'), 'samples' );
my (@n, @r);

# check delete_paths

tie my %t, 'Tie::IxHash';

%t = ( foo => [ 'bar', 'baz', '/grelb' ],
	bar => { spam => { and => 'eggs' },
	     '/boog' => { this => [qw/should be gone/] } },
       baz => [ qw/further data here/] );

my @del = Bento::MakeModel::delete_paths( \%t );
is_deeply [@del], [ ['{foo}[2]','grelb'], ['{bar}{boog}','boog']], 'delete paths';



$mod_y = LoadFile(File::Spec->catdir($samplesd,"icdc-model.yml"));
$specced_props = Set::Scalar->new( @{$mod_y->{Nodes}{prior_therapy}{Props}} );

$obj = Bento::MakeModel->new(LOG_LEVEL=>$FATAL);
$obj->read_input( File::Spec->catdir($samplesd,"icdc-model.yml"),
		  File::Spec->catdir($samplesd,"icdc-model-props.yml"));

diag "check original (before overlay)";
$nodes = Set::Scalar->new($obj->nodes);
ok $nodes->has('demographic'), "demographic node present...";
$d_props = Set::Scalar->new(map {$_->name} $obj->get_node('demographic')->props);
ok $d_props->has('breed'), "...has 'breed' property";
ok !$d_props->has('species'), "...but has no 'species' property";
ok $nodes->has('cycle'), "cycle node present";
$del_pt_props = Set::Scalar->new(qw/total_dose therapy_type total_number_of_doses_steroid/);
$pt_props = Set::Scalar->new(map {$_->name} $obj->get_node('prior_therapy')->props);
ok $specced_props->is_subset($pt_props), "prior_therapy has all specified props...";
ok $del_pt_props->is_subset($pt_props), "including props to be deleted";

diag "check overlay...";
$obj = Bento::MakeModel->new(LOG_LEVEL=>$FATAL);
$obj->read_input( File::Spec->catdir($samplesd,"icdc-model.yml"),
		  File::Spec->catdir($samplesd,"icdc-model-props.yml"),
		  File::Spec->catdir($samplesd,"deleting-overlay.yml"),
		 );

# check merge is correct - following data appear in overlay but not basic model
$got_nodes = Set::Scalar->new($obj->nodes);
$got_d_props = Set::Scalar->new(map {$_->name} $obj->get_node('demographic')->props);
$got_pt_props = Set::Scalar->new(map {$_->name} $obj->get_node('prior_therapy')->props);
ok !$got_nodes->has('cycle'), "now cycle DNE";
ok !$got_d_props->has('breed'), "demographics no longer has 'breed' prop...";
ok $got_d_props->has('species'), "but now has 'species' property";
ok $del_pt_props->is_disjoint($got_pt_props), "prior_therapy props to be deleted are gone...";
ok $got_pt_props->has('fred'), ".. and there's fred";

done_testing;
