"""
bento_meta.util.changelog

Common functions shared by changelog generation scripts
"""
import configparser
import logging
from typing import Generator, Optional

logger = logging.getLogger(__name__)


def get_initial_changeset_id(config_file_path: str) -> int:
    """Gets initial changeset id from changelog config file"""
    config = configparser.ConfigParser()
    config.read(config_file_path)
    try:
        return config.getint(section="changelog", option="changeset_id")
    except (configparser.NoSectionError, configparser.NoOptionError) as error:
        logger.error(f"Reading changeset ID failed: {error}")
        raise


def changeset_id_generator(config_file_path: str) -> Generator[int, None, None]:
    """Generates sequential changeset IDs by reading the latest ID from a config file."""
    i = get_initial_changeset_id(config_file_path)
    while True:
        yield i
        i += 1


def update_config_changeset_id(config_file_path: str, new_changeset_id: int) -> None:
    """Updates changelog config file with new changeset id."""
    config = configparser.ConfigParser()
    config.read(config_file_path)
    config.set(section="changelog", option="changeset_id", value=str(new_changeset_id))
    with open(file=config_file_path, mode="w", encoding="UTF-8") as config_file:
        config.write(fp=config_file)
