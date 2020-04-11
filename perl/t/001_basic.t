use Test::More;
use File::Spec;
use Bento::MakeModel;
use lib '../lib';

my $sampdir = File::Spec->catdir(-d "samples" ? "." : "t", "samples");

use_ok('Bento::Meta::Model');

ok $met = Bento::Meta::Model->new('ICDC');
isa_ok ($met, 'Bento::Meta::Model');

ok $mm = Bento::MakeModel->new(files => [File::Spec->catfile($sampdir,'icdc-model.yml'),
                                 File::Spec->catfile($sampdir,'icdc-model-props.yml')]), "load ICDC model from YAML";



done_testing;
