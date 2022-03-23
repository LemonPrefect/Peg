import base64
import hashlib
import hmac
import logging
import time
import urllib.parse

logger = logging.getLogger(__name__)


def HmacSHA1(code: str, key: str) -> str:
    """
    hmacsha1 for string with key as string, string returns.
    :param code: string to hmacsha1
    :param key: key for the hmacsha1
    :return: hmacsha1 string for the code
    """
    return hmac.new(key.encode(), code.encode(), hashlib.sha1).hexdigest()


def SHA1(res: str) -> str:
    """
    sha1 for string with result hexed.
    :param res: string to sha1
    :return: sha1 string for the res
    """
    return hashlib.sha1(res.encode("UTF-8")).hexdigest()


def MD5(res: bytes) -> str:
    """
    MD5 for bytes with result base64ed.
    :param res: bytes to MD5
    :return: MD5 string for the res base64ed
    """
    return base64.b64encode(hashlib.md5(res).digest()).decode()


def GetAuth(secretId: str, secretKey: str, method: str, params: dict, headers: dict, pathname="/") -> str:
    """
    Authorization for COS requests.
    :param secretId: secretId for the request
    :param secretKey: secretKey for the request
    :param method: request method like "get"
    :param params: request params to be sign
    :param headers: request headers to be sign
    :param pathname: path in the bucket to access, default value is "/"
    :return: signature header string
    """
    # url encode the params and headers for the consistence of signature and data sent
    for key in headers.keys():
        if type(headers[key]) is str:
            headers[key] = urllib.parse.quote(headers[key]).replace("/", "%2F")
    for key in params.keys():
        if type(params[key]) is str:
            params[key] = urllib.parse.quote(params[key]).replace("/", "%2F")

    method = method.lower()

    # single request expires in 900 seconds
    secondTimestampNow = round(time.time())
    expires = secondTimestampNow + 900

    # calculate signature as COS demanded, reference https://cloud.tencent.com/document/product/436/7778
    signature = HmacSHA1("\n".join([
        "sha1",
        f"{secondTimestampNow};{expires}",
        SHA1("\n".join([
            method,
            pathname,
            CompactPairs(params),
            CompactPairs(headers),
            ""])
        ),
        ""]), HmacSHA1(f"{secondTimestampNow};{expires}", secretKey))

    logger.debug(signature)

    return "&".join([f"q-sign-algorithm=sha1",
                     f"q-ak={secretId}",
                     f"q-sign-time={secondTimestampNow};{expires}",
                     f"q-key-time={secondTimestampNow};{expires}",
                     f"q-header-list={CompactKeys(headers)}",
                     f"q-url-param-list={CompactKeys(params)}",
                     f"q-signature={signature}"])


def CompactKeys(obj: dict) -> str:
    """
    Join sorted keys of a dict with ';'.
    :param obj: dict like {"a": "abc", "b": "bcd"}
    :return: string like "a;b"
    """
    keys = list(obj.keys())
    keys.sort()
    return ";".join(keys)


def CompactPairs(obj: dict) -> str:
    """
    Join sorted key=value pairs with '&'.
    :param obj: dict like {"a": "abc", "b": "bcd"}
    :return: string like "a=abc&b=bcd"
    """
    keys = list(obj.keys())
    keys.sort()
    return "&".join([f"{key}={obj[key]}" for key in keys])

