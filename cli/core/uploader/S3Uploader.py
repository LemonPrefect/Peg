# -*- coding=utf-8
import boto3
from cli.core.uploader import Uploader
from cli.core.File import File


class S3Uploader(Uploader):
    """
    S3 SDK uploader, multi-thread.
    """
    def __init__(self, sessionToken: str, accessKeyId: str, secretAccessKey: str, info: str, endpoint: str):
        """
        Initiate the uploader.
        :param sessionToken: token
        :param accessKeyId: secretId
        :param secretAccessKey: secretKey
        :param info: bucket info given by DogeCloud
        :param endpoint: endpoint as COS'
        """
        super(S3Uploader, self).__init__(sessionToken, accessKeyId, secretAccessKey, info)

        self._uploader = boto3.client(
            "s3",
            aws_access_key_id=accessKeyId,
            aws_secret_access_key=secretAccessKey,
            aws_session_token=sessionToken,
            endpoint_url=endpoint
        )

    def upload(self, file: File, path: str, callbackProgress=None):
        """
        Upload file use S3 SDK, multi-thread.
        :param file: File object with local file path as File.path
        :param path: path in the bucket for the file
        :param callbackProgress: callback function for the progress
        :return: uploading object of the S3
        """
        return self._uploader.upload_fileobj(
            open(f"{file.path}/{file.name}", "rb"),
            self.prefix,
            f"{path}{file.name}",
            Callback=callbackProgress
        )
