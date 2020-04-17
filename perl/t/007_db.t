use Test::More;
use Test::Warn;
use Test::Exception;
use IPC::Run qw/run/;
use Neo4j::Bolt;
use lib '../lib';
use Bento::Meta::Model::ObjectMap;
use Bento::Meta::Model::Node;

my $ctr_name = "test$$";
my $img = 'maj1/test-db-bento-meta';

####
diag "Starting docker container '$ctr_name' with image $img";
my @startcmd = split / /,
  "docker run -d -P --name $ctr_name $img";
my @portcmd = split / /, "docker container port $ctr_name";
my @stopcmd = split / /,"docker kill $ctr_name";
my @rmcmd = split / /, "docker rm $ctr_name";

my ($in, $out, $err);
unless (run(['docker'],'<pty<',\$in,'>pty>',\$out)) {
  plan skip_all => "Docker not available for test database setup: skipping.";
}
run \@startcmd, \$in, \$out, \$err;
if ($err) {
  diag "docker error: $err";
}
sleep 10;
$in=$err=$out='';
run \@portcmd, \$in, \$out, \$err;
my ($port) = grep /7687.tcp/, split /\n/,$out;
($port) = $port =~ m/([0-9]+)$/;
####
ok my $cxn = Neo4j::Bolt->connect("bolt://localhost:$port"), 'create neo4j connection';
SKIP : {
  skip "Can't connect to test db: ".$cxn->errmsg, 1 unless $cxn->connected;
  ok my $omap = "Bento::Meta::Model::Node"->object_map(
   {
      simple => [
        [model => 'model'],
        [handle => 'handle']
       ],
      object => [
        [ 'concept' => ':has_concept>',
          'Bento::Meta::Model::Concept' => 'concept' ],
       ],
      collection => [
        [ 'props' => ':has_property>',
          'Bento::Meta::Model::Property' => 'property' ],
       ]
     }
   ), "create ObjectMap for Node class";

  ok $omap->bolt_cxn($cxn), 'set db connection';
  isa_ok $Bento::Meta::Model::Node::OBJECT_MAP,'Bento::Meta::Model::ObjectMap';
  my $res;
  is $omap, $Bento::Meta::Model::Node::OBJECT_MAP, "pointer same";
  $DB::single=1;
  ok $res = $cxn->run_query('match (a:node) return id(a) limit 1');
  ok my ($n_id) = $res->fetch_next;
  my $node = Bento::Meta::Model::Node->new({neoid => $n_id});
  ok $node->get(), "get node with neoid $n_id";
  is $node->dirty, 0, "node clean";
  is $node->concept->dirty, -1, "object property dirty with -1";
  
  
}

done_testing;

END {
  diag "Stopping container $ctr_name";
  run \@stopcmd;
  diag "Removing container $ctr_name";  
  run \@rmcmd;
}
