# -*- coding=utf-8
import hashlib
import logging
import httpx as requests
from ..Exception import CliRequestError, CliKeyError
from ..User import User

logger = logging.getLogger(__name__)


def SmsHelper(phone: str) -> None:
    """
    Query SMS verify code for login.
    :param phone: phone number in China Mainland which represented an account
    """
    session = requests.Client(
        base_url="https://api.dogecloud.com/user/",
        verify=False
    )

    # check if the account is exists
    response = session.post(
        url="/checkphone.json",
        data={
            "phone": phone
        })
    data = response.json()
    logger.debug(response.request)
    logger.debug(data)
    if response.status_code != 200 or data.get("code", -1) != 200:
        raise CliRequestError(response)
    if data.get("data", {}).get("exists", False) is not True:
        raise CliKeyError(data)

    # send verification code
    response = session.post(
        url="/sms.json",
        data={
            "phone": phone,
            "stype": "login"
        })
    data = response.json()
    logger.debug(response.request)
    logger.debug(data)
    if response.status_code != 200 or data.get("code", -1) != 200:
        raise CliRequestError(response)


def Login(type: str, phone: str, code: str) -> User:
    """
    Login to get user token, Object User returns.
    :param type: "vcode" for SMS login, "password" for password login
    :param phone: phone number represented an account
    :param code: vcode from SMS received or password
    :return: User object with token
    """
    if type == "vcode":
        response = requests.post(
            url="https://api.dogecloud.com/user/login.json",
            data={
                "ltype": type,
                "phone": phone,
                "vcode": code,
                "remember": "1"
            })
    elif type == "password":
        response = requests.post(
            url="https://api.dogecloud.com/user/login.json",
            data={
                "ltype": type,
                "phone": phone,
                "noguess": hashlib.md5(f"{code}~dogecloud~password".encode()).hexdigest(),
                "remember": "1"
            })
    else:
        raise CliKeyError({
            "message": "unsupported login method"
        })

    data = response.json()
    logger.debug(response.request)
    logger.debug(data)
    if response.status_code != 200 or data.get("code", -1) != 200:
        raise CliRequestError(response)
    # if data.get("data", {}).get("exists", False) is not True:
    #     raise CliKeyError(data)
    #
    # assert response.status_code == 200
    #
    # data = response.json()
    # assert data["code"] == 200

    token = response.cookies.get("token", None)
    if not token:
        raise CliKeyError(dict(response.cookies))

    return User(token)
