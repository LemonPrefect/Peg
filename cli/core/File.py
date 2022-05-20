class File:
    def __init__(self, name: str, path: str, _type: str, _hash=None, fileSize=0, _time=None):
        self.name = name
        self.hash = _hash
        self.fileSize = fileSize
        self.time = _time
        self.type = _type
        self.path = path

