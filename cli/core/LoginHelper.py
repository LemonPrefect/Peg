import hashlib
import httpx as requests

from .User import User


def SmsHelper(phone: str):
    session = requests.Client(
        base_url="https://api.dogecloud.com/user/",
        verify=False
    )

    response = session.post(
        url="/checkphone.json",
        data={
            "phone": phone
        })
    assert response.status_code == 200

    data = response.json()
    assert data["code"] == 200
    assert data["data"]["exists"] is True

    response = session.post(
        url="/sms.json",
        data={
            "phone": phone,
            "stype": "login"
        })
    assert response.status_code == 200

    data = response.json()
    assert data["code"] == 200


def Login(type: str, phone: str, code: str):
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
        raise KeyError("unsupported login method")

    assert response.status_code == 200

    data = response.json()
    assert data["code"] == 200

    token = response.cookies["token"]
    return User(token)
