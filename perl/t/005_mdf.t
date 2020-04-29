use Test::More;
use Test::Exception;
use Test::Warn;
use Log::Log4perl qw/:easy/;
use File::Spec;
use lib '../lib';
use strict;

#Log::Log4perl->easy_init($WARN);

use_ok('Bento::Meta::MDF');
my $d = (-e 't' ? 't' : '.');

throws_ok { Bento::Meta::MDF->create_model( File::Spec->
  catfile($d,'samples','icdc-model.yml'), File::Spec->
  catfile($d,'samples','icdc-model-props.yml')) } qr/expecting model handle/,
  "die when files only are provided (without model handle)";

throws_ok { Bento::Meta::MDF->create_model('boog') } qr/req list of files/,
  "die when no files provided";

ok my $model = Bento::Meta::MDF->create_model(test => File::Spec->catfile($d,'samples','test-model.yml')), "load MDF into model";

is_deeply [ sort map {$_->handle} $model->nodes ],
  [sort qw/case sample file diagnosis/], 'nodes present';
is_deeply [ sort map {$_->triplet} $model->edges ],
  [sort qw/of_case:sample:case of_case:diagnosis:case of_sample:file:sample
         derived_from:file:file derived_from:sample:sample/], 'edges present';

is_deeply [ sort map {$_->handle} $model->props ],
  [sort qw/case_id patient_id sample_type amount md5sum file_name file_size
           disease days_to_sample workflow_id id/], 'props present';

ok my $file = $model->node('file'), 'file node';
is_deeply [sort map {$_->handle} $file->props],
  [sort qw/md5sum file_name file_size/], 'file props correct';

is $file->props('md5sum')->value_domain, 'regexp', 'correct domain for md5sum';
ok $file->props('md5sum')->pattern, 'md5sum has pattern attribute';

ok my $amount = $model->prop('sample:amount'), "amount prop";
is $amount->value_domain, 'number', 'correct domain';
is $amount->units, 'mg', 'has correct units';
ok my $file_size = $model->prop('file:file_size'), "file_size prop";
is $file_size->units, 'Gb;Mb', 'has correct units (delim by semicolon)';

ok my ($derived_from) = $model->edge('derived_from:sample:sample' ), "derived_from edge";
is scalar values %{ $derived_from->props }, 1, "has one prop";
is( ($derived_from->props)[0]->handle, 'id', 'correct general property');

ok my ($derived_from) = $model->edges_by_dst( $model->node('file') ), "derived_from edge";
is scalar values %{ $derived_from->props }, 1, "has one prop";
is( ($derived_from->props)[0]->handle, 'workflow_id', 'correct local property');

is scalar $model->edges_in($model->node('case')), 2, 'edges in to case node';
is scalar $model->edges_out($model->node('diagnosis')), 1, 'edges out of diagnosis node';

ok my $sample = $model->node('sample'), 'sample node';
ok my $sample_type = $sample->props('sample_type'), 'sample_type property';
is $sample_type->value_domain, 'value_set';
isa_ok($sample_type->value_set, 'Bento::Meta::Model::ValueSet');
is_deeply [sort $sample_type->values], [qw/normal tumor/], 'term values for prop';


done_testing;
