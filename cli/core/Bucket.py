import base64
import logging
import httpx as requests

from .User import User
from .File import File
from .uploader import Uploader
from .utilities.PathUtils import NormalizePath
from .Exception import CliRequestError, CliKeyError

logger = logging.getLogger(__name__)


class Bucket:
    """
    OSS Bucket
    """

    def __init__(self, name: str, user: User, uploader=None):
        """
        Initiate an OSS Bucket.
        :param name: name of OSS bucket without suffix, as imagebutter
        :param user: User object with token in it
        :param uploader: FileUploader object, core.uploader
        """
        self.name = name
        self.user = user
        self.uploader = uploader

        self.session = requests.Client(
            base_url="https://api.dogecloud.com/oss/",
            verify=False,
            timeout=5,
            cookies={"token": self.user.token},
            headers={"authorization": "COOKIE"}
        )
        response = self.session.post(
            url="/bucket/info.json",
            data={"name": self.name}
        )

        data = response.json()
        logger.debug(response.request)
        logger.debug(data)
        if response.status_code != 200 or data.get("code", 0) != 200:
            raise CliRequestError(response)

        self.prefix = data.get("data", {}).get("system_domain", "").split(".")[0]
        self.source = data.get("data", {}).get("source_name", "")
        self.core = data.get("data", {}).get("sdk_info", {}).get("core", "")
        self.domain = data.get("data", {}).get("default_domain", "")

        if self.prefix == "" or self.source == "" or self.core == "" or self.domain == "":
            raise CliKeyError(data)

    def list(self, limit=100, path="/", _continue="") -> list:
        """
        List a bucket file directory, or buckets, continue supported.
        :param limit: quantity of the list items return in a time
        :param path: directory to list
        :param _continue: continue from the item index and fetch a LIMIT quantity of item
        :return: List of File object
        """

        path = NormalizePath(path)

        response = self.session.post(
            url="/file/list.json",
            data={
                "bucket": self.name,
                "prefix": path if path != "/" else "",  # If listing the root, nothing needed.
                "continue": _continue,
                "limit": limit
            })
        data = response.json()
        logger.debug(response.request)
        logger.debug(data)
        if response.status_code != 200 or data.get("code", 0) != 200:
            raise CliRequestError(response)

        return [File(
            name=file.get("key", ""),
            _hash=file.get("hash", ""),
            fileSize=file.get("fsize", ""),
            _time=file.get("time", ""),
            _type=file.get("type", ""),
            path=path
        ) for file in data.get("data", {}).get("files", {})]

    def upload(self, file: File, path: str, callbackProgress=None):
        """
        Upload file to the bucket.
        :param file: File object with local path in it.
        :param path: bucket file path.
        :param callbackProgress: callback progress indicator, default None
        :return: uploading object
        """

        path = NormalizePath(path)

        if self.uploader is None:
            raise CliKeyError({"data": "No uploader set."})

        return self.uploader.upload(file, path, callbackProgress)

    def remove(self, files: [File], callbackProgress=None) -> None:
        """
        Remove files/folders from bucket.
        :param files: list of file object, file/folder are both accepted
        :param callbackProgress: callback progress indicator, default None
        :return: error raises if failed
        """
        # split folders and files into different array
        folders = []
        for file in files:
            if file.type == "folder":
                folders.append(base64.b64encode(f"{file.path}{file.name}".encode()).decode()
                               .translate(str.maketrans("+/=", "-_ ")).strip())
            else:
                files.append(f"{file.path}{file.name}")
            files.remove(file)

        logger.debug(files)
        logger.debug(folders)

        if callbackProgress:
            callbackProgress("prepared", 0)

        # remove folders separately.
        if folders:
            for folder in folders:
                logger.debug(f"removed folder {folder}")
                response = self.session.post(
                    url="/file/folderdelete.json",
                    params={
                        "bucket": self.name,
                        "key": folder
                    }
                )
                data = response.json()
                logger.debug(response.request)
                logger.debug(data)
                if response.status_code != 200 or data.get("code") != 200:
                    raise CliRequestError(response)

                if callbackProgress:
                    callbackProgress(folder, folders.index(folder) + 1 / (len(folders) + len(files)))

        # remove file in a time using an array.
        if len(files) > 0:
            response = self.session.post(
                url="/file/delete.json",
                params={
                    "bucket": self.name,
                },
                json=files
            )
            data = response.json()

            logger.debug(response.request)
            logger.debug(data)

            if response.status_code != 200 or data.get("code") != 200:
                raise CliRequestError(response)

            if callbackProgress:
                callbackProgress(str(files), 1)

    def move(self, src: str, dst: str) -> None:
        """
        Move file from source to destination.
        :param src: source file path
        :param dst: destination file path
        :return: error raises if failed
        """
        response = self.session.post(
            url="/file/move.json",
            params={
                "src": base64.b64encode(f"{self.name}:{src}".encode()).decode(),
                "dest": base64.b64encode(f"{self.name}:{dst}".encode()).decode()
            }
        )
        data = response.json()
        logger.debug(response.request)
        logger.debug(data)
        if response.status_code != 200 or data.get("code", 0) != 200:
            raise CliRequestError(response)

    def link(self, file: File, isSecure=False) -> str:
        """
        Generate the url of the file source, https if isSecure is True, otherwise http will be used.
        :param file: file object from bucket
        :param isSecure: https or http
        :return: url for the file source in the bucket
        """
        return f"{'https' if isSecure else 'http'}://{self.domain}/{file.path}{file.name}"

    def mkdir(self, fullPath: str):
        """
        Make a directory in the bucket.
        :param fullPath: path from the root of bucket, as image/folder
        :return: error raises if failed
        """
        fullPath = NormalizePath(fullPath)

        response = self.session.post(
            url="/upload/put.json",
            params={
                "bucket": self.name,
                "key": fullPath
            }
        )
        data = response.json()
        logger.debug(response.request)
        logger.debug(data)
        if response.status_code != 200 or data.get("code") != 200:
            raise CliRequestError(response)

    def setUploader(self, uploader: Uploader) -> bool:
        """
        Set an uploader for the bucket.
        :param uploader: uploader object
        :return: false if failed
        """
        if not isinstance(uploader, Uploader):
            return False
        self.uploader = uploader
        return True
