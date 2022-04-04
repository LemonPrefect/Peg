# -*- coding=utf-8
import base64
import json
import logging
from cli.core.Exception import CliKeyError

logger = logging.getLogger(__name__)


class Uploader:
    """
    Uploader for file uploading in different ways.
    """
    def __init__(self, sessionToken: str, accessKeyId: str, secretAccessKey: str, info: str):
        """
        Initiate the uploader.
        :param sessionToken: token
        :param accessKeyId: secretId
        :param secretAccessKey: secretKey
        :param info: bucket info given by DogeCloud
        """
        self.sessionToken = sessionToken
        self.accessKeyId = accessKeyId
        self.secretAccessKey = secretAccessKey

        info += '=' * (4 - (len(info) % 4))
        info = json.loads(base64.b64decode(info))

        self.bucket = info.get("bucket", None)
        self.region = info.get("region", None)
        self.prefix = info.get("preprefix", "").strip("/")

        logger.debug(info)

        if self.bucket is None or self.region is None or self.prefix == "":
            raise CliKeyError(info)
