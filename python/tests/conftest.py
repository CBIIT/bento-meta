import pytest
import requests
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
  bolt_port = docker_services.port_for("bento-neo4j",7687)
  http_port = docker_services.port_for("bento-neo4j",7474)
  bolt_url = "bolt://{}:{}".format(docker_ip,bolt_port)
  http_url = "http://{}:{}".format(docker_ip,http_port)
  sleep(wait)
  docker_services.wait_until_responsive(
    timeout=5.0, pause=1.0, check=lambda: is_responsive(http_url)
  )
  return (bolt_url,http_url)

@pytest.fixture(scope="session")
def plain_neo4j(docker_services, docker_ip):
  bolt_port = docker_services.port_for("plain-neo4j",7687)
  http_port = docker_services.port_for("plain-neo4j",7474)
  bolt_url = "bolt://{}:{}".format(docker_ip,bolt_port)
  http_url = "http://{}:{}".format(docker_ip,http_port)
  sleep(wait)
  docker_services.wait_until_responsive(
    timeout=30.0, pause=0.5, check=lambda: is_responsive(http_url)
  )
  return (bolt_url,http_url)

