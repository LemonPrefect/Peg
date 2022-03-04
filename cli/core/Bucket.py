import base64
import httpx as requests
from .User import User
from . import UploadHelper


class Bucket:
    def __init__(self, name: str, user: User):
        self.name = name
        self.user = user
        self.session = requests.Client(base_url="https://api.dogecloud.com/oss/",
                                       verify=False,
                                       timeout=5,
                                       cookies={"token": self.user.token},
                                       headers={"authorization": "COOKIE"})
        response = self.session.post(
            url="/bucket/info.json",
            data={
                "name": self.name
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200

        self.prefix = data["data"]["system_domain"].split(".")[0]
        self.source = data["data"]["source_name"]
        self.core = data["data"]["sdk_info"]["core"]
        self.domain = data["data"]["default_domain"]

    class File:
        def __init__(self, name: str, path: str, _type: str, _hash=None, fileSize=0, _time=None):
            self.name = name
            self.hash = _hash
            self.fileSize = fileSize
            self.time = _time
            self.type = _type
            self.path = path

    def list(self, limit=100, path="", _continue="") -> list:
        if not path.endswith("/"):
            path += "/"
        if path.startswith("/"):
            path = path[1:]

        response = self.session.post(
            url="/file/list.json",
            data={
                "bucket": self.name,
                "prefix": path,
                "continue": _continue,
                "limit": limit
            })
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200

        return [self.File(
            name=file["key"],
            _hash=file["hash"],
            fileSize=file["fsize"],
            _time=file["time"],
            _type=file["type"],
            path=path
        ) for file in data["data"]["files"]]

    def upload(self, file: File, path: str, callbackProgress=None) -> str:
        if not path.endswith("/"):
            path += "/"
        if path.startswith("/"):
            path = path[1:]

        if "COS" == self.core:
            return UploadHelper.CosHelper(self, file, path, callbackProgress)
        raise KeyError(f"Undefined OSS core {self.core}")

    def remove(self, files, callbackProgress=None):
        folders = []
        for file in files:
            if file.type == "folder":
                folders.append(base64.b64encode(f"{file.path}{file.name}".encode()).decode()
                               .translate(str.maketrans("+/=", "-_ ")).strip())
            else:
                files.append(f"{file.path}{file.name}")
            files.remove(file)

        if callbackProgress:
            callbackProgress("prepared", 0)
        if len(folders) > 0:
            for folder in folders:
                response = self.session.post(
                    url="/file/folderdelete.json",
                    params={
                        "bucket": self.name,
                        "key": folder
                    }
                )
                assert response.status_code == 200
                data = response.json()
                assert data["code"] == 200

                if callbackProgress:
                    callbackProgress(folder, folders.index(folder) + 1 / (len(folders) + len(files)))

        if len(files) > 0:
            response = self.session.post(
                url="/file/delete.json",
                params={
                    "bucket": self.name,
                },
                json=files
            )
            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 200

            if callbackProgress:
                callbackProgress(str(files), 1)

    def move(self, src: str, dst: str):
        response = self.session.post(
            url="/file/move.json",
            params={
                "src": base64.b64encode(f"{self.name}:{src}".encode()).decode(),
                "dest": base64.b64encode(f"{self.name}:{dst}".encode()).decode()
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200

        pass

    def link(self, file: File, isSecure=False) -> str:
        return f"{'https' if isSecure else 'http'}://{self.domain}/{file.path}{file.name}"

    def mkdir(self, fullPath: str):
        if not fullPath.endswith("/"):
            fullPath += "/"
        if fullPath.startswith("/"):
            fullPath = fullPath[1:]

        response = self.session.post(
            url="/upload/put.json",
            params={
                "bucket": self.name,
                "key": fullPath
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
