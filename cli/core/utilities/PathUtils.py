# -*- coding=utf-8
import logging

logger = logging.getLogger(__name__)


def KeySplit(key: str) -> tuple:
    """
    Separate the filename and the path from the key of the OSS given.
    :param key: string like images/essay/123/
    :return: tuple(path, filename) like ('images/essay', '123')
    """
    # Clean the path delimiter for compatibility.
    key = key.replace("\\", "/").replace("//", "/")
    key = key.strip("/")

    tokens = key.split("/")
    filename = tokens[-1]
    tokens.remove(tokens[-1])
    path = "/".join(tokens)
    logger.debug(f"Path: {path}, Filename {filename}")
    return path, filename


def NormalizePath(path: str) -> str:
    """
    Parse a path with no leading '/' and ends with '/'.
    :param path: string path to a file/folder without filename.
    :return: string path parsed.
    """
    logger.debug(f"Parsing path {path}")
    return path.replace("\\", "/").replace("//", "/").strip("/") + "/"

