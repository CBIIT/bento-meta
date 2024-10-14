import pytest
import requests
import string
import subprocess
import logging
from warnings import warn
from requests.exceptions import ConnectionError
from time import sleep
from pdb import set_trace

wait = 25


def is_responsive(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return True
    except ConnectionError:
        return False


@pytest.fixture(scope="session")
def bento_neo4j(docker_services, docker_ip):
    bolt_port = docker_services.port_for("bento-neo4j", 7687)
    http_port = docker_services.port_for("bento-neo4j", 7474)
    bolt_url = "bolt://{}:{}".format(docker_ip, bolt_port)
    http_url = "http://{}:{}".format(docker_ip, http_port)
    sleep(wait)
    docker_services.wait_until_responsive(
        timeout=15.0, pause=1.0, check=lambda: is_responsive(http_url)
    )
    return (bolt_url, http_url)

  
@pytest.fixture(scope="session")
def plain_neo4j(docker_services, docker_ip):
    bolt_port = docker_services.port_for("plain-neo4j", 7687)
    http_port = docker_services.port_for("plain-neo4j", 7474)
    bolt_url = "bolt://{}:{}".format(docker_ip, bolt_port)
    http_url = "http://{}:{}".format(docker_ip, http_port)
    sleep(wait)
    docker_services.wait_until_responsive(
        timeout=30.0, pause=0.5, check=lambda: is_responsive(http_url)
    )
    return (bolt_url, http_url)

  
@pytest.fixture(scope="session")
def mdb(docker_services, docker_ip):
    bolt_port = docker_services.port_for("mdb", 7687)
    http_port = docker_services.port_for("mdb", 7474)
    bolt_url = "bolt://{}:{}".format(docker_ip, bolt_port)
    http_url = "http://{}:{}".format(docker_ip, http_port)
    sleep(wait)
    docker_services.wait_until_responsive(
        timeout=30.0, pause=0.5, check=lambda: is_responsive(http_url)
    )
    return (bolt_url, http_url)

  
@pytest.fixture(scope="session")
def mdb_versioned(docker_services, docker_ip):
    bolt_port = docker_services.port_for("mdb-versioned", 7687)
    http_port = docker_services.port_for("mdb-versioned", 7474)
    bolt_url = "bolt://{}:{}".format(docker_ip, bolt_port)
    http_url = "http://{}:{}".format(docker_ip, http_port)
    sleep(wait)
    docker_services.wait_until_responsive(
        timeout=30.0, pause=1.0, check=lambda: is_responsive(http_url)
    )
    return (bolt_url, http_url)

@pytest.fixture()
def test_paths(model="ICDC", handle="diagnosis", phandle="disease_term", key="Class", value="primary", nanoid="abF32k"):
    tpl = [
        "/models",
        "/models/count",
        "/model/$model/nodes",
        "/model/$model/nodes/count",
        "/model/$model/node/$handle",
        "/model/$model/node/$handle/properties",
        "/model/$model/node/$handle/properties/count",
        "/model/$model/node/$handle/property/$phandle",
        "/model/$model/node/$handle/property/$phandle/terms",
        "/model/$model/node/$handle/property/$phandle/terms/count",
        "/model/$model/node/$handle/property/$phandle/term/$value",
        "/tags",
        "/tags/count",
        "/tag/$key/values",
        "/tag/$key/values/count",
        "/tag/$key/$value/entities",
        "/tag/$key/$value/entities/count",
        "/term/$value",
        "/term/$value/count",
        "/id/$nanoid"
        ]
    return [string.Template(x).
            safe_substitute(model=model, handle=handle, phandle=phandle,
                            key=key, value=value, nanoid=nanoid) for x in tpl]

                                               
