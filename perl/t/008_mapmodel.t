use Test::More;
use Test::Warn;
use Test::Exception;
use IPC::Run qw/run/;
use Neo4j::Bolt;
use lib '../lib';
use Log::Log4perl qw/:easy/;
use Bento::Meta::Model;

Log::Log4perl->easy_init($FATAL);
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
else {
  sleep 10;
}
$in=$err=$out='';
run \@portcmd, \$in, \$out, \$err;
my ($port) = grep /7687.tcp/, split /\n/,$out;
($port) = $port =~ m/([0-9]+)$/;
####
ok my $cxn = Neo4j::Bolt->connect("bolt://localhost:$port"), 'create neo4j connection';
SKIP : {
  skip "Can't connect to test db: ".$cxn->errmsg, 1 unless $cxn->connected;

  ok my $model = Bento::Meta::Model->new('ICDC', $cxn), "create Model obj with Neo4j mapping";
  ok $model->get, "load model from db";

  ok my ($dbc) = $cxn->run_query('match (n:node) where n.model="ICDC" return count(n)')
    ->fetch_next,"fetch no. db nodes";
  is scalar $model->nodes, $dbc, 'number of nodes correct';

  ok my ($dbc) = $cxn->run_query('match (n:relationship) where n.model="ICDC" return count(n)')
    ->fetch_next, "fetch no. db edges";
  is scalar $model->edges, $dbc, 'number of edges correct';

  ok my ($dbc) = $cxn->run_query('match (n:node)-->(p:property) where n.model="ICDC" return count(p)')
    ->fetch_next,"fetch no. db props";
  is scalar $model->props, $dbc, 'number of props correct';

  ok my $res = $cxn->run_query(<<QRY);
    match (s:node)<-[:has_src]-(e:relationship)-[:has_dst]->(d:node)
    where (e.model = 'ICDC')
    return s,e,d
QRY
  while (my ($s,$e,$d) = $res->fetch_next) {
    my $triplet = join(':',$e->{properties}{handle},
                       $s->{properties}{handle},
                       $d->{properties}{handle});
    is $model->edge($triplet)->src->handle, $s->{properties}{handle}, "edge $triplet src";
    is $model->edge($triplet)->dst->handle, $d->{properties}{handle}, "edge $triplet dst";
  }

  ok $res = $cxn->run_query(<<QRY);
    match (n:node)-[:has_property]->(p:property)
    where (n.model = 'ICDC')
    return n, collect(p);
QRY
  while (my ($n, $pp) = $res->fetch_next) {
    for my $p (@$pp) {
      my $k = join(':',$$n{properties}{handle},$$p{properties}{handle});
      ok my $mp = $model->prop($k), "property $k in model";
      if ($mp) {
        is $mp->neoid,
          ,$$p{id},"property '$$p{properties}{handle}' in model props";
        is $model->node($n->{properties}{handle})->props($p->{properties}{handle})->neoid, $p->{id}, "model has property '$$p{properties}{handle}' for node '$$n{properties}{handle}'";
      }
      else {
        push @not, [$k => $p];
      }
    }
  }

  
  1;
}

done_testing;

END {
  diag "Stopping container $ctr_name";
  run \@stopcmd;
  diag "Removing container $ctr_name";  
  run \@rmcmd;
}
