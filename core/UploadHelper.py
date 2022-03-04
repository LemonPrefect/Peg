import os.path
import time
import boto3
import magic
import httpx as requests

from . import UploadUtils


def CosHelper(bucket, file, path: str, callbackProgress=None):
    response = bucket.session.post(
        url="/file/info.json",
        params={
            "simple": 1,
            "bucket": bucket.name
        },
        json=[f"{path}{file.name}"]
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200

    response = bucket.session.post(
        url="/upload/auth.json",
        json={
            "scope": f"{bucket.name}:{path}{file.name}",
            "deadline": round(time.time()) + 900
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200

    token = data["data"]["uploadToken"]
    response = requests.get(
        url=f"https://{bucket.source}",
        params={
            "uploads": "",
            "prefix": f"{bucket.prefix}/{path}{file.name}"
        },
        headers={
            "content-type": magic.from_file(file.path, mime=True),
            "authorization": UploadUtils.GetAuth(token=token,
                                                 method="get",
                                                 params={
                                                     "uploads": "",
                                                     "prefix": f"{bucket.prefix}/{path}{file.name}"
                                                 },
                                                 headers={},
                                                 ),
            "x-cos-security-token": token.split(":")[0],
            "x-cos-storage-class": "Standard"
        })
    assert response.status_code == 200

    response = requests.post(
        url=f"https://{bucket.source}/{bucket.prefix}/{path}{file.name}",
        params={
            "uploads": ""
        },
        headers={
            "authorization": UploadUtils.GetAuth(token=token,
                                                 method="post",
                                                 params={
                                                     "uploads": ""
                                                 },
                                                 headers={
                                                     "x-cos-storage-class": "Standard"
                                                 },
                                                 pathname=f"/{bucket.prefix}/{path}{file.name}"
                                                 ),
            "x-cos-security-token": token.split(":")[0],
            "x-cos-storage-class": "Standard"
        })
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
            url=f"https://{bucket.source}/{bucket.prefix}/{path}{file.name}",
            params={
                "partnumber": x + 1,
                "uploadid": uploadId
            },
            headers={
                "authorization": UploadUtils.GetAuth(token=token,
                                                     method="put",
                                                     params={
                                                         "partnumber": x + 1,
                                                         "uploadid": uploadId
                                                     },
                                                     headers={
                                                         "content-length": len(uploadFileBytes)
                                                     },
                                                     pathname=f"/{bucket.prefix}/{path}{file.name}"
                                                     ),
                "x-cos-security-token": token.split(":")[0],
            }, data=uploadFileBytes)
        assert response.status_code == 200

        etag = response.headers["Etag"][1:-1]
        etagXml += f"<Part><PartNumber>{x + 1}</PartNumber><ETag>&quot;{etag}&quot;</ETag></Part>"
        if callbackProgress:
            callbackProgress(etag, (x + 1) / fileSlice)
    data = f"""
    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <CompleteMultipartUpload>{etagXml}</CompleteMultipartUpload>
    """.encode()

    response = requests.post(
        url=f"https://{bucket.source}/{bucket.prefix}/{path}{file.name}",
        params={
            "uploadid": uploadId
        },
        headers={
            "user-agent": "Forest/0.0.1",
            "content-type": "application/xml",
            "content-md5": f"{UploadUtils.MD5(data)}",
            "authorization": UploadUtils.GetAuth(token=token,
                                                 method="post",
                                                 params={
                                                     "uploadid": uploadId
                                                 },
                                                 headers={
                                                     "content-md5": f"{UploadUtils.MD5(data)}"
                                                 },
                                                 pathname=f"/{bucket.prefix}/{path}{file.name}"
                                                 ),
            "x-cos-security-token": token.split(":")[0],
        }, data=data)
    assert response.status_code == 200

    return response.content.decode()


def OssHelper():
    # TODO: OSS bucket upload
    pass


def S3Helper(bucket, file, path: str):

    # These lines are intended to be duplicated as CosHelper and S3Helper will work separately.
    # A hacky way for the s3 endpoint.

    response = bucket.session.post(
        url="/upload/auth.json",
        json={
            "scope": f"{bucket.name}:{path}{file.name}",
            "deadline": round(time.time()) + 900
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200

    sessionToken, accessKeyId, secretAccessKey, info = tuple(data["data"]["uploadToken"].split(":"))

    # info = info + '=' * (4 - (len(info) % 4))
    # info = json.loads(base64.b64decode(info))

    s3 = boto3.client(
        "s3",
        aws_access_key_id=accessKeyId,
        aws_secret_access_key=secretAccessKey,
        aws_session_token=sessionToken,
        endpoint_url=f"https://{bucket.source}"
    )
    return s3.upload_fileobj(open(file.path, "rb"), bucket.prefix, f"{path}{file.name}")
