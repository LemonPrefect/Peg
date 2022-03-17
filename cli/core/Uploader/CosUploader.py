from qcloud_cos import CosS3Client, CosConfig
from cli.core.Uploader import Uploader


class COSUploader(Uploader):

    def __init__(self, sessionToken, accessKeyId, secretAccessKey, info):
        super(COSUploader, self).__init__(sessionToken, accessKeyId, secretAccessKey, info)

        self._uploader = CosS3Client(
            CosConfig(
                Region=self.region,
                SecretId=accessKeyId,
                SecretKey=secretAccessKey,
                Token=self.sessionToken,
                Domain=None
            )
        )

    def upload(self, file, path, maxThread=10, partSize=20, callbackProgress=None):
        return self._uploader.upload_file(
            Bucket=self.bucket,
            LocalFilePath=file.path,
            Key=f"{self.prefix}{path}{file.name}",
            PartSize=partSize,
            MAXThread=maxThread,
            progress_callback=callbackProgress
        )
