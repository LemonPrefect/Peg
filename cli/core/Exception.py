# -*- coding=utf-8
import httpx as requests


class CliException(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return str(self.message)


class CliRequestError(CliException):
    def __init__(self, response: requests.Response):
        self.message = f"Status code: {response.status_code}\n{response.text}"


class CliKeyError(CliException):
    def __init__(self, data: dict):
        self.message = str(data)


class CliUploaderOptionError(CliException):
    def __init__(self, uploader, options: dict):
        self.message = f"Uploader: {str(uploader)}\nOptions: {str(options)}"

