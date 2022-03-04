import base64
import hashlib
import hmac
import time
import urllib.parse


def HmacSHA1(code: str, key: str) -> str:
    return hmac.new(key.encode(), code.encode(), hashlib.sha1).hexdigest()


def SHA1(res: str) -> str:
    return hashlib.sha1(res.encode("UTF-8")).hexdigest()


def MD5(res: bytes) -> str:
    return base64.b64encode(hashlib.md5(res).digest()).decode()


def GetAuth(token: str, method: str, params: dict, headers: dict, pathname="/") -> str:
    # url encode the params and headers for the consistent of signature and data sent
    for key in headers.keys():
        if type(headers[key]) is str:
            headers[key] = urllib.parse.quote(headers[key]).replace("/", "%2F")
    for key in params.keys():
        if type(params[key]) is str:
            params[key] = urllib.parse.quote(params[key]).replace("/", "%2F")

    secretId = token.split(":")[1]
    secretKey = token.split(":")[2]
    method = method.lower()
    secondTimestampNow = round(time.time())
    expires = secondTimestampNow + 900
    signature = HmacSHA1("\n".join(["sha1", f"{secondTimestampNow};{expires}", SHA1(
        "\n".join([method, pathname, _compactPairs(params), _compactPairs(headers), ""])
    ), ""]), HmacSHA1(f"{secondTimestampNow};{expires}", secretKey))

    return "&".join([f"q-sign-algorithm=sha1",
                     f"q-ak={secretId}",
                     f"q-sign-time={secondTimestampNow};{expires}",
                     f"q-key-time={secondTimestampNow};{expires}",
                     f"q-header-list={_compactKeys(headers)}",
                     f"q-url-param-list={_compactKeys(params)}",
                     f"q-signature={signature}"])


def _compactKeys(obj) -> str:
    keys = list(obj.keys())
    keys.sort()
    return ";".join(keys)


def _compactPairs(obj: dict) -> str:
    keys = list(obj.keys())
    keys.sort()
    return "&".join([f"{key}={obj[key]}" for key in keys])
