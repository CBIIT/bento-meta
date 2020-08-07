# model-tool - reference Bento implementation in Perl

`model-tool` allows you to validate, view and graph a graph model specified in the [bento-mdf](../../../README.md) format.

We recommend using the Docker image to run `model-tool`.

## Running `model-tool` with Docker

To use model-tool without having to install Perl dependencies, you can
use a pre-built Docker image. The script
[`model-tool-d`](./bin/model-tool-d) should make this very
simple on Linux and MacOS:

* Get [Docker](https://docker.com)
* Clone this repo

        git clone https://github.com/CBIIT/bento-mdf.git

* Do following at command line:

        $ cd bento-mdf/drivers/Perl/make-model
        $ 
        $ export MODELTOOL_DIR=$(pwd) # set MODELTOOL_DIR to absolute path to repo dir
        $ export PATH=$PATH:$MODELTOOL_DIR/make-model/bin # put the script in your path
        $ cd <your-model-desc> # go to where the model description files are
        $ model-tool-d -T model.txt <your-model>*.yml # try creating a node/property table

## Installing `model-tool` on your machine

* MakeModel is written in Perl. If you don't have Perl,
[get it](https://www.perl.org/get.html). On Windows, I recommend
Strawberry Perl.

* Get [GraphViz](http://www.graphviz.org/) if you want to use the
graphic output feature.

* Clone this repo 

        git clone https://github.com/CBIIT/bento-mdf.git

* Move to `make-model` directory 

        cd bento-mdf/drivers/Perl/make-model

* Easy build:

  * Get the "cpanminus" tool:

        curl -L https://cpanmin.us | perl - App::cpanminus     # or wget -O - https://cpanmin.us | perl - App::cpanminus

  * Run cpanm to install

        cpanm .

    which will pull in all dependencies, run tests and install the script.

* Try it:

        model-tool

  and the Usage hints should display:

```
$ bin/model-tool 
FATAL: Nothing to do!
 (2019/08/23 15:37:10 in main::)
Usage:
      model-tool [-g <graph-out-file>] [-s <output-dir>] [-j <json-out-file>] 
                 [-T <table-out-file>] <input.yaml> [<input2.yaml> ...]
         [-d dir_to_search [-d another_dir...]]
      -g : create an SVG of model defined in input.yamls
      -T : output a table of nodes and properties
      -a : output all nodes, including unlinked nodes
      -v : verbosity (-v little ... -vvvv lots)
      -W : show all warnings ( = -vvv )
      --dry-run : emit log msg, but no output files
```

