# set env BENTO_LONG_TEST to review accessors for every element in test MDF.
use Test::More;
use Test::Exception;
use Try::Tiny;
use File::Spec;
use lib '../lib';
use Log::Log4perl::Level;
use Bento::MakeModel;
my $samplesd = File::Spec->catdir( (-d 't' ? 't' : '.'), 'samples' );
my $obj;


ok $obj = Bento::MakeModel->new(
  LOG_LEVEL=>$FATAL,
  files => [ File::Spec->catdir($samplesd,"try.yml") ]
 );

is_deeply $obj->{_univ_node_props}, { mayHave => ['desc'], mustHave => ['id'] }, "unp";
is_deeply $obj->{_univ_rel_props}, { mayHave => ['desc'], mustHave => ['id'] }, "urp";
ok my $m = $obj->model;
ok $m->node('boog')->prop('id'), 'boog has id';
ok $m->node('boog')->prop('desc'), 'boog has desc';
ok $m->node('goob')->prop('id'), 'goob has id';
ok $m->node('goob')->prop('desc'), 'goob has desc';
ok $m->edge('goob_of','goob','boog')->prop('id'), 'goob_of (rel) has id';
ok $m->edge('goob_of','goob','boog')->prop('desc'), 'goob_of (rel) has desc';

done_testing;

