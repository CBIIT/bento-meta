use Test::More;
use File::Spec;
use Log::Log4perl qw/:easy/;
use lib '../lib';

Log::Log4perl->easy_init($FATAL);
my $sampdir = File::Spec->catdir(-d "samples" ? "." : "t", "samples");

use_ok('Bento::Meta::Model');

ok $met = Bento::Meta::Model->new('ICDC');
isa_ok ($met, 'Bento::Meta::Model');


done_testing;
