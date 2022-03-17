import boto3

from cli.core.Uploader import Uploader


class S3Uploader(Uploader):

    def __init__(self, sessionToken, accessKeyId, secretAccessKey, info, endpoint):
        super(S3Uploader, self).__init__(sessionToken, accessKeyId, secretAccessKey, info)

        self._uploader = boto3.client(
            "s3",
            aws_access_key_id=accessKeyId,
            aws_secret_access_key=secretAccessKey,
            aws_session_token=sessionToken,
            endpoint_url=endpoint
        )

    def upload(self, file, path):
        return self._uploader.upload_fileobj(
            open(file.path, "rb"),
            self.prefix,
            f"{path}{file.name}"
        )
