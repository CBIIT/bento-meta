# NAME

Bento::Meta::Model - object bindings for Bento Metamodel Database

# SYNOPSIS

    # empty model with name $handle:
    $model = Bento::Meta::Model->new('Test');
    # pull model from database - add bolt connection with Neo4j::Bolt
    $model = Bento::Meta::Model->new('ICDC',Neo4j::Bolt->connect('bolt://localhost:7687))
    # connect model to db after creating 
    $model = Bento::Meta::Model->new('CTDC');
    $model->set_bolt_cxn( Neo4j::Bolt->connect('bolt://localhost:7687') );
    $model->get(); # pulls nodes, properties, relationships with model => 'CTDC'

    # read a model from MDF YAML files:
    use Bento::Meta::MDF;
    $model = Bento::Meta::MDF->create_model(qw/icdc-model.yml icdc-model-props.yml/);
    # connect it and push to db
    $model->set_bolt_cxn( Neo4j::Bolt->connect('bolt://localhost:7687') );
    $model->put(); # writes all to db

    # build model from scratch: add, change, and remove entities

    $model = Bento::Meta::Model->new('Test');
    
    # create some nodes and add them
    ($case, $sample, $file) = 
       map { Bento::Meta::Model::Node->new({handle => $_}) } qw/case sample file/;
    $model->add_node($case);
    $model->add_node($sample);
    $model->add_node($file);
    
    # create some relationships (edges) between nodes
    $of_case = Bento::Meta::Model::Edge->new({ 
      handle => 'of_case',
      src => $sample,
      dst => $case });
    
    $has_file = Bento::Meta::Model::Edge->new({
      handle => 'has_file',
      src => $sample,
      dst => $file });
      
    $model->add_edge($of_case);
    $model->add_edge($has_file);

    # create some properties and add to nodes or to edges
    $case_name = Bento::Meta::Model::Property->new({
      handle => 'name',
      value_domain => 'string' });
    $workflow_type = Bento::Meta::Model::Property->new({
      handle => 'workflow_type',
      value_domain => 'value_set' });

    $model->add_prop( $case => $case_name );
    $model->add_prop( $has_file => $workflow_type );

    # add some terms to a property with a value set (i.e., enum)

    $model->add_terms( $workflow_type => qw/wdl cwl snakemake/ );
     

# DESCRIPTION

# METHODS

## $model object

### Write methods

- new($handle)
- add\_node($node\_or\_init)
- add\_edge($edge\_or\_init)
- add\_prop($node\_or\_edge, $prop\_or\_init)
- add\_terms($prop, @terms\_or\_inits)
- rm\_node($node)
- rm\_edge($edge)
- rm\_prop($prop)

### Read methods

- @nodes = $model->nodes()
- $node = $model->node($name)
- @props = $model->props()
- $prop = $model->prop($name)
- $edge = $model->edge($triplet)
- @edges = $model->edges\_in($node)
- @edges = $modee->edges\_out($node)
- @edges = $model->edge\_by\_src()
- @edges = $model->edge\_by\_dst()
- @edges = $model->edge\_by\_type()

## $node object

- $node->name()
- $node->category()
- @props = $node->props()
- $prop = $node->props($name)
- @tags = $node->tags()

## $edge object

- $edge->type()
- $edge->name()
- $edge->is\_required()
- $node = $edge->src()
- $node = $edge->dst()
- @props = $edge->props()
- $prop = $edge->props($name)
- @tags = $edge->tags()

## $prop object

- $prop->name()
- $prop->is\_required()
- $value\_type = $prop->type()
- @acceptable\_values = $prop->values()
- @tags = $prop->tags()
