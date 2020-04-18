use Test::More;
use Test::Exception;
use Test::Warn;
use lib '../lib';
use strict;

use_ok('Bento::Meta::Model');

our $B = 'Bento::Meta::Model';
our $N = "${B}::Node";
our $E = "${B}::Edge";
our $V = "${B}::ValueSet";
our $T = "${B}::Term";
our $P = "${B}::Property";

ok my $model = $B->new('test'), 'create model';
isa_ok($model, $B);
dies_ok {$B->new()} 'new reqs $handle';
is $model->handle, 'test', 'model handle set';

ok my $case = $N->new({
  handle => 'case',
  model => 'test',
  tags => ['florp', 'blerg']
 }), 'create Node';
isa_ok($case, $N);
isa_ok($case, "${B}::Entity");
is $case->handle, 'case', 'attr1';
is $case->model, 'test', 'attr2';
is_deeply [$case->tags],[qw/florp blerg/], 'attr3';

ok $case->set_props( 'days_to_enrollment' => $P->new({handle => 'days_to_enrollment'})), "add a property 'by hand'";
ok my $ret = $model->add_node($case), 'add Node obj';
is $ret, $case, 'add_node returns the Node';
ok $model->prop('case:days_to_enrollment'), "pre-existing property added to model";

ok $ret = $model->add_node({ handle => 'sample'}), 'add node with init hash';
is $ret->model, 'test', 'add_node sets model attr';
is scalar $model->nodes, 2, 'two nodes';

ok my $case_id = $P->new({ handle => 'case_id', value_domain => 'string' }), 'create Property';
isa_ok($case_id, $P);
  
ok $ret = $model->add_prop($case, $case_id), 'added Property to Node';
is $ret, $case_id, 'add_prop returns the Property';
ok $ret = $model->add_prop($case, {handle=>'patient_id',value_domain=>'string'}), 'add prop with init hash';
is $ret->model, $model->handle, 'add_props sets model attr';
is $ret->value_domain,'string', 'prop attr correct';
is $case->props('patient_id'), $ret, 'retrieve prop from Node obj';
is $model->prop('case:patient_id'), $ret, 'retrieve prop from Model obj';

ok $case = $model->node('case'), "get case node";
ok my $sample = $model->node('sample'), "get sample node";
ok my $of_case = $E->new({handle => 'of_case',
                          src => $sample,
                          dst => $case}), 'create Edge obj';
isa_ok($of_case,$E);
isa_ok($of_case->src, $N);
isa_ok($of_case->dst, $N);
is $of_case->triplet, 'of_case:sample:case', 'edge triplet string';
ok $of_case->set_props('operator', $P->new({handle=>'operator'})), "add prop to edge 'by hand'";

ok my $ret = $model->add_edge($of_case), 'add Edge object';
ok $model->prop('of_case:sample:case:operator'), "pre-existing prop added to model list"; 
is $ret, $of_case, 'add_edge returns Edge';
is $model->edge('of_case',$sample,$case), $of_case, 'retrieve edge by components';
is $model->edge('of_case','sample','case'), $of_case, 'retrieve edge by handles';
is $model->edge('of_case:sample:case'), $of_case, 'retrieve edge by triplet';

ok $ret = $model->add_edge({handle => 'has_sample',
                            src => $case,
                            dst => $sample}), "add edge with init hash";
is $ret->triplet,'has_sample:case:sample', 'correct triplet string';

warnings_like { $model->add_edge({ handle => 'of_program',
                                   src => $N->new({ handle => 'project' }),
                                   dst => $N->new({ handle => 'program' }) }) }
  [qr/source node 'project' is not yet/,qr/dest\S+ node 'program' is not yet/],
  "add edge - auto add new nodes with warnings";
is $model->node('project')->model, 'test', "project node added";
is $model->node('program')->model, 'test', "program node added";

ok $ret = $model->add_prop($of_case, { handle => 'consent_on', value_domain => 'datetime' }), 'add prop to edge';

is $ret->handle, 'consent_on', 'prop handle set';
is $of_case->props('consent_on'), $ret, 'retrieve prop from Edge obj';
is $model->prop('of_case:sample:case:consent_on'), $ret, 'retrieve prop from Model obj';

warning_like { $model->add_prop( $N->new({handle => 'diagnosis'}), {handle=>'disease'}) } qr/node 'diagnosis' is not yet/, "new node in add_prop warns";

warning_like { $model->add_prop( $E->new({handle => 'of_case',
                                          src => $model->node('diagnosis'),
                                          dst => $model->node('case')}),
                                 { handle => 'primary_dx',
                                   value_domain => 'boolean' }) }
  qr/edge 'of_case' is not yet/, "new edge in add_prop warns";

is scalar $model->edges_by_type('of_case'), 2, 'edges_by_type of_case correct';
is scalar $model->edges_by_src('sample'), 1, 'edges_by_src sample correct';
is scalar $model->edges_by_dst('case'), 2, 'edges_by_dst case correct';

ok my @edges = $model->edges_in($case), 'edges_in';
is_deeply [ sort map {$_->triplet} @edges], [sort qw/of_case:sample:case of_case:diagnosis:case/], 'edges_in correct';
ok @edges = $model->edges_out($sample), 'edges_out';
is_deeply [ sort map {$_->triplet} @edges], [qw/of_case:sample:case/], 'edges_in correct';                              

# test properties with value sets

warning_like { $model->add_terms($model->prop('of_case:diagnosis:case:primary_dx'), 'boog') }
  qr/domain 'boolean', not 'value_set'/;
dies_ok { $model->add_terms($model->edge( 'of_case:diagnosis:case' ), 'boog') }
  'add_terms dies if arg1 not Prop';
ok my $disease = $model->prop('diagnosis:disease'), 'get disease property';
ok $ret = $model->add_terms($disease, 'CRS', 'halitosis', 'fungusamongus');
isa_ok($ret, $V);
is_deeply [sort $disease->values], [sort qw/CRS halitosis fungusamongus/], "terms set and values correct";
ok $ret = $model->add_terms($disease, $T->new({value => 'rockin_pneumonia'})), "add Term object";
is_deeply [sort $disease->values], [sort qw/CRS halitosis fungusamongus rockin_pneumonia/], "term added to existing set";

my $blerg = $N->new({handle => 'blerg'});
warning_like { $model->rm_node($blerg) } qr/'blerg' not contained/, "warn when trying to rm node already not in model";

my $project = $model->node('project');
ok $model->add_prop($project, {handle=>'short_name'}), 'add a prop';
ok $project->props('short_name'), "there it is";
ok $model->prop('project:short_name'), 'also in model';

warning_like { $model->rm_node( $project ) } qr/can't remove node 'project'/, "warn when trying to rm node that has edges";
my $of_program = $model->edge('of_program:project:program');
ok $model->add_prop($of_program, {handle => 'scroob'});
ok $of_program->props('scroob');
ok $model->prop('of_program:project:program:scroob');
ok $ret = $model->rm_edge( $of_program ), 'rm edge';
isa_ok($ret, $E);
ok !$model->edge('of_program:project:program'), 'really gone';
ok !$model->prop('of_program:project:program:scroob'), 'prop gone from model';
ok $of_program->props('scroob'), 'but still on edge';


ok $ret = $model->rm_node( $model->node('project') ), 'now can remove node';
isa_ok( $ret, $N);
is $ret->handle, 'project', 'removed node correct';
ok !$model->node('project'), 'really gone';
ok !$model->prop('project:short_name'), 'prop also gone from model...';
ok $ret->props('short_name'), 'but still lives on the node';


ok $ret = $model->rm_prop( $case_id ), "rm node prop";
is $ret, $case_id;
ok !$case->props('case_id'), "also gone from case";

my $consent_on = $model->prop('of_case:sample:case:consent_on');
ok $ret = $model->rm_prop($consent_on), 'rm edge prop';
is $ret, $consent_on;
ok !$model->edge('of_case:sample:case')->props('consent_on'), "also gone from edge";

done_testing;
