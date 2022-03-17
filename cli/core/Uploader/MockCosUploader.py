import logging
import os
import magic
import httpx as requests

from cli.core import UploadUtils
from cli.core.Uploader import Uploader


class MockCosUploader(Uploader):

    def __init__(self, sessionToken, accessKeyId, secretAccessKey, info, endpoint):
        super(MockCosUploader, self).__init__(sessionToken, accessKeyId, secretAccessKey, info)
        self.endpoint = endpoint
        logging.debug(f"Token: {self.sessionToken}, accessKeyId: {self.accessKeyId}, endpoint: {self.endpoint}")
        logging.info("MockCosUploader Initialized")

    def upload(self, file, path, callbackProgress=None):
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
        logging.debug(response.text)
        logging.info(response.status_code)
        assert response.status_code == 200

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
        logging.debug(response.text)
        logging.info(response.status_code)
        assert response.status_code == 200

        index = response.content.decode().index("<UploadId>")
        uploadId = response.content.decode()[index + 10:index + 84]
        bytesFile = open(f"{file.path}", "rb")
        file.fileSize = os.path.getsize(file.path)
        fileSlice = round(file.fileSize / 1024 / 1024 / 2)
        fileSlice = 1 if fileSlice <= 2 else fileSlice
        etagXml = ""

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
            logging.debug(response.text)
            logging.info(response.status_code)
            assert response.status_code == 200

            etag = response.headers["Etag"][1:-1]
            etagXml += f"<Part><PartNumber>{x + 1}</PartNumber><ETag>&quot;{etag}&quot;</ETag></Part>"
            logging.info(etag)
            logging.debug(etagXml)
            if callbackProgress:
                callbackProgress(etag, (x + 1) / fileSlice)
        data = f"""
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <CompleteMultipartUpload>{etagXml}</CompleteMultipartUpload>
        """.encode()

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
        logging.debug(response.text)
        logging.info(response.status_code)
        assert response.status_code == 200

        return response.content.decode()

