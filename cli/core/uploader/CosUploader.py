# -*- coding=utf-8
from qcloud_cos import CosS3Client, CosConfig
from cli.core.uploader import Uploader
from cli.core.File import File


class CosUploader(Uploader):
    """
    COS SDK uploader, multi-thread.
    """
    def __init__(self, sessionToken: str, accessKeyId: str, secretAccessKey: str, info: str):
        """
        Initiate the uploader.
        :param sessionToken: token
        :param accessKeyId: secretId
        :param secretAccessKey: secretKey
        :param info: bucket info given by DogeCloud
        """
        super(CosUploader, self).__init__(sessionToken, accessKeyId, secretAccessKey, info)

        self._uploader = CosS3Client(
            CosConfig(
                Region=self.region,
                SecretId=accessKeyId,
                SecretKey=secretAccessKey,
                Token=self.sessionToken,
                Domain=None
            )
        )

    def upload(self, file: File, path: str, callbackProgress=None):
        """
        Upload file use COS SDK, multi-thread.
        :param file: File object with local file path as File.path
        :param path: path in the bucket for the file
        :param callbackProgress: callback function for the progress
        :return: uploading object of the COS
        """
        return self._uploader.upload_file(
            Bucket=self.bucket,
            LocalFilePath=file.path,
            Key=f"{self.prefix}{path}{file.name}",
            progress_callback=callbackProgress
        )
