# -*- coding=utf-8
import logging
import os
import magic
import httpx as requests
from cli.core.Exception import CliRequestError
from cli.core.utilities import UploadUtils
from cli.core.uploader import Uploader
from cli.core.File import File

logger = logging.getLogger(__name__)


class MockCosUploader(Uploader):
    """
    COS SDK mock uploader, single thread and 2MB file slice.
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
        super(MockCosUploader, self).__init__(sessionToken, accessKeyId, secretAccessKey, info)
        self.endpoint = endpoint
        logger.debug(f"Token: {self.sessionToken}, accessKeyId: {self.accessKeyId}, endpoint: {self.endpoint}")

    def upload(self, file: File, path: str, callbackProgress=None) -> str:
        """
        Upload file with slice of 2MB, single thread.
        :param file: File object with local path as its path
        :param path: path in the bucket for the file
        :param callbackProgress: callback function for the progress
        :return: final upload status
        """
        response = requests.get(
            url=self.endpoint,
            params={
                "uploads": "",
                "prefix": f"{self.prefix}/{path}{file.name}"
            },
            headers={
                "content-type": magic.from_file(file.path, mime=True),
                "authorization": UploadUtils.GetAuth(
                    secretId=self.accessKeyId,
                    secretKey=self.secretAccessKey,
                    method="get",
                    params={
                     "uploads": "",
                     "prefix": f"{self.prefix}/{path}{file.name}"
                    },
                    headers={},
                    ),
                "x-cos-security-token": self.sessionToken,
                "x-cos-storage-class": "Standard"
            })
        data = response.text
        logger.debug(response.request)
        logger.debug(data)
        if response.status_code != 200:
            raise CliRequestError(response)

        response = requests.post(
            url=f"{self.endpoint}/{self.prefix}/{path}{file.name}",
            params={
                "uploads": ""
            },
            headers={
                "authorization": UploadUtils.GetAuth(
                    secretId=self.accessKeyId,
                    secretKey=self.secretAccessKey,
                    method="post",
                    params={
                     "uploads": ""
                    },
                    headers={
                     "x-cos-storage-class": "Standard"
                    },
                    pathname=f"/{self.prefix}/{path}{file.name}"
                    ),
                "x-cos-security-token": self.sessionToken,
                "x-cos-storage-class": "Standard"
            })
        data = response.text
        logger.debug(response.request)
        logger.debug(data)
        if response.status_code != 200:
            raise CliRequestError(response)

        index = response.content.decode().index("<UploadId>")
        uploadId = response.content.decode()[index + 10:index + 84]

        bytesFile = open(f"{file.path}", "rb")
        file.fileSize = os.path.getsize(file.path)
        fileSlice = round(file.fileSize / 1024 / 1024 / 2)
        fileSlice = 1 if fileSlice <= 2 else fileSlice

        etagXml = ""

        # put slices
        for x in range(fileSlice):
            if x == fileSlice - 1:
                uploadFileBytes = bytesFile.read()
            else:
                uploadFileBytes = bytesFile.read(1024 * 1024 * 2)
            response = requests.put(
                url=f"{self.endpoint}/{self.prefix}/{path}{file.name}",
                params={
                    "partnumber": x + 1,
                    "uploadid": uploadId
                },
                headers={
                    "authorization": UploadUtils.GetAuth(
                        secretId=self.accessKeyId,
                        secretKey=self.secretAccessKey,
                        method="put",
                        params={
                         "partnumber": x + 1,
                         "uploadid": uploadId
                        },
                        headers={
                         "content-length": len(uploadFileBytes)
                        },
                        pathname=f"/{self.prefix}/{path}{file.name}"
                        ),
                    "x-cos-security-token": self.sessionToken,
                }, data=uploadFileBytes)
            data = response.text
            logger.debug(response.request)
            logger.debug(data)
            if response.status_code != 200:
                raise CliRequestError(response)

            etag = response.headers["Etag"][1:-1]
            etagXml += f"<Part><PartNumber>{x + 1}</PartNumber><ETag>&quot;{etag}&quot;</ETag></Part>"
            logger.debug(etagXml)

            if callbackProgress:
                callbackProgress(etag, (x + 1) / fileSlice)
        data = f"""
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <CompleteMultipartUpload>{etagXml}</CompleteMultipartUpload>
        """.encode()

        # concat slices, complete file uploading
        response = requests.post(
            url=f"{self.endpoint}/{self.prefix}/{path}{file.name}",
            params={
                "uploadid": uploadId
            },
            headers={
                "content-type": "application/xml",
                "content-md5": f"{UploadUtils.MD5(data)}",
                "authorization": UploadUtils.GetAuth(
                    secretId=self.accessKeyId,
                    secretKey=self.secretAccessKey,
                    method="post",
                    params={
                     "uploadid": uploadId
                    },
                    headers={
                     "content-md5": f"{UploadUtils.MD5(data)}"
                    },
                    pathname=f"/{self.prefix}/{path}{file.name}"
                    ),
                "x-cos-security-token": self.sessionToken,
            }, data=data)
        data = response.text
        logger.debug(response.request)
        logger.debug(data)
        if response.status_code != 200:
            raise CliRequestError(response)

        return response.content.decode()

