# Docker Neo4j for testing

The [Dockerfile](./Dockerfile) will set up a dockerized neo4j v3.5 container, using
the database in the [data](./data) subdirectory and the [neo4j.conf](./neo4j.conf)
in this directory. 

To set up, 

* cp -R the database (i.e., the ``graph.db`` directory, or other) from your local 
machine to [./data/databases](./data/databases). 

* Update the [neo4j.conf](./neo4j.conf) to use this database

        ...
        # The name of the database to mount
        dbms.active_database=graph.db  # or whatever
        ...

* On your local machine, in the this directory, run 

        docker build -t <your_tag_here> .

* To run it on randomly selected high ports:

        docker run -P -d <your_tag_here>

* To map the ports directly to localhost

        docker run -p 7687:7687 -p 7473:7473 -p 7474:7474 -d <your_tag_here>



