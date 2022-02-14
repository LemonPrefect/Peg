import json
import os
import re
import urllib.parse

import click
import httpx as requests
from tqdm import tqdm

from core import User, Bucket, LoginHelper
from core.User import User
from core.Bucket import Bucket


@click.group()
def main():
    pass


@main.command(
    help="Upload a file or a folder."
)
@click.option(
    "--file",
    "-f", type=click.STRING,
    required=True,
    help="file/folder path."
)
@click.option(
    "--bucket",
    "-b", type=click.STRING,
    required=True,
    help="bucket name as same as ls shows."
)
@click.option(
    "--path",
    "-p", type=click.STRING,
    required=True,
    help="path from the / of bucket to where the FILE should located."
)
def upload(file, bucket, path):
    if not os.path.exists(file):
        click.echo(f"file {file} doesn't exist.")
        return

    token = _feastToken()
    if not token:
        click.echo("Need login first.")
        return
    token = str(token)

    try:
        bucket = Bucket(bucket, User(token))
    except AssertionError:
        click.echo("Something went wrong, please check the args.")
        click.echo("at Bucket.Create/Bucket.List")
        return

    if os.path.isdir(file):
        file = file.strip("/").strip("\\")
        path = path.strip("/").strip()
        _path = os.path.abspath(os.path.dirname(file))
        for root, dirs, _files in os.walk(file):
            for file in _files:
                fileAbsPath = os.path.abspath(os.path.join(root, file))
                uploadPath = "/".join(re.split(r'[/|//|\\\\|\\]', fileAbsPath.replace(_path, "#")))
                uploadAbsPath = f"{path}{'' if path == '' else '/'}{uploadPath[1:]}".replace(file, "")
                uploadFile = bucket.File(
                    name=file,
                    path=fileAbsPath,
                    _type="file"
                )
                bar = tqdm(total=100, ncols=120, desc=file, ascii=True)
                try:
                    bucket.upload(
                        file=uploadFile,
                        path=uploadAbsPath,
                        callbackProgress=lambda etag, progress:
                        _progress(bar, progress=round(progress * 100), message=etag)
                    )
                except AssertionError:
                    click.echo("Something went wrong, please check the args.")
                    click.echo("at Bucket.Upload")
                    return

    else:
        fileAbsPath = os.path.abspath(os.path.join(os.path.dirname(file), file))
        filename = os.path.basename(file)
        print(filename)
        uploadFile = bucket.File(
            name=filename,
            path=fileAbsPath,
            _type="file"
        )
        bar = tqdm(total=100, ncols=120, desc=filename, ascii=True)
        try:
            bucket.upload(
                file=uploadFile,
                path=path,
                callbackProgress=lambda etag, progress:
                _progress(bar, progress=round(progress * 100), message=etag)
            )
        except AssertionError:
            click.echo("Something went wrong, please check the args.")
            click.echo("at Bucket.Upload")
            return


@main.command(
    help="List buckets or directory."
)
@click.option(
    "--bucket",
    "-b",
    type=click.STRING,
    required=False,
    help="bucket name, leave blank with also path if need to list buckets."
)
@click.option(
    "--path",
    "-p",
    type=click.STRING,
    required=False,
    default="/",
    help="path to list for, such as /images. leave blank with also bucket if need to list buckets."
)
def ls(bucket, path):
    token = _feastToken()
    if not token:
        click.echo("Need login first.")
        return
    token = str(token)

    if not bucket and not path:
        response = requests.get(
            url="https://api.dogecloud.com/oss/bucket/list.json",
            cookies={"token": token},
            headers={"authorization": "COOKIE"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        click.echo(f"{'id':<10}\t{'name':<30}\t{'stored'}")
        for bucket in data["data"]["buckets"]:
            click.echo(f"{bucket['id']:<10}\t{bucket['name']:<30}\t{(int(bucket['space']) / 1024 / 1024):.2f} MiB")
        return

    try:
        bucket = Bucket(bucket, User(token))
        files = bucket.list(limit=2147483647, path=path)
    except AssertionError:
        click.echo("Something went wrong, please check the args.")
        click.echo("at Bucket.Create/Bucket.List")
        return

    click.echo(f"Directory /{path.rstrip('/').lstrip('/')}, {len(files)} files/directories")
    for file in files:
        click.echo(f"{file.name.lstrip(path):<60}\t{(int(file.fileSize) / 1024):.2f} KiB")


@main.command(
    help="Login with vcode or password."
)
@click.option(
    "--phone",
    "-p",
    type=click.types.STRING,
    required=True,
    help="phone number for the account."
)
@click.option(
    "--method",
    "-m",
    type=click.types.Choice(["password", "vcode"]),
    required=True,
    help="login method, password or vcode for SMS TOTP (not stable)."
)
def login(method, phone):
    token = _feastToken()
    if token:
        click.echo(f"token {token} is on duty.")
        return
    click.echo(f"Login with phone {phone}, method {method}.")
    input("If the args are correct, press enter.")
    if method == "vcode":
        click.echo("SMS could be fail to send, if so, try again later or use password to login.")
        LoginHelper.SmsHelper(phone)
        click.echo("SMS has been sent to you.")
        code = click.prompt("Enter the vcode")
    else:
        code = click.prompt("Enter the password", hide_input=True)

    try:
        user = LoginHelper.Login(method, phone, code)
    except AssertionError:
        click.echo("Something went wrong, please check the args.")
        click.echo("at LoginHelper.Login")
        return

    click.echo("Token acquired.")
    open("./config.json", "w").write(json.dumps({
        "token": user.token
    }))
    click.echo("token saved.")


@main.command(
    help="Overwrite the config file to nothing."
)
def logout():
    if _feastToken():
        open("./config.json", "w").write("")
        click.echo("Config overwritten.")


@main.command(
    help="Move a file to the specific directory."
)
@click.option(
    "--bucket",
    "-b",
    type=click.STRING,
    required=True,
    help="bucket name, leave blank with also path if need to list buckets."
)
@click.option(
    "--src",
    "-s", type=click.STRING,
    required=True,
    help="file/folder path from the / of the bucket."
)
@click.option(
    "--dst",
    "-d", type=click.STRING,
    required=True,
    help="path from the / of bucket to where the FILE should located with filename."
)
def mv(bucket, src, dst):
    src = str(src).lstrip("/")
    dst = str(dst).lstrip("/")

    if src.endswith("/") or dst.endswith("/"):
        click.echo("Please move file only. Folders will be created otherwise.")
        return

    token = _feastToken()
    if not token:
        click.echo("Need login first.")
        return
    token = str(token)

    try:
        bucket = Bucket(bucket, User(token))
        bucket.move(src, dst)
    except AssertionError:
        click.echo("Something went wrong, please check the args.")
        click.echo("at Bucket.Create/Bucket.Move")
        return

    pass


@main.command(
    help="Get a link for a file or files in the folder."
)
@click.option(
    "--bucket",
    "-b",
    type=click.STRING,
    required=False,
    help="bucket name, leave blank with also path if need to list buckets."
)
@click.option(
    "--file",
    "-f", type=click.STRING,
    required=True,
    help="file/folder path from the / of the bucket."
)
@click.option(
    "--ssl",
    "-s",
    type=click.types.BOOL,
    required=True,
    help="whether use SSL."
)
def link(bucket, file, ssl):
    token = _feastToken()
    if not token:
        click.echo("Need login first.")
        return
    token = str(token)

    try:
        bucket = Bucket(bucket, User(token))
    except AssertionError:
        click.echo("Something went wrong, please check the args.")
        click.echo("at Bucket.Create")
        return

    if str(file).endswith("/"):
        try:
            files = bucket.list(limit=2147483647, path=file[1:] if str(file).startswith("/") else file)
        except AssertionError:
            click.echo("Something went wrong, please check the args.")
            click.echo("at Bucket.List")
            return

        for file in files:
            if file.type == "file":
                click.echo(f"{'https' if ssl else 'http'}://{bucket.domain}/{urllib.parse.quote(file.name)}")
    else:
        file = file.strip("/").strip()
        click.echo(f"{'https' if ssl else 'http'}://{bucket.domain}/{file}")


@main.command(
    help="Remove a folder or a file."
)
@click.option(
    "--bucket",
    "-b", type=click.STRING,
    required=True,
    help="bucket name as same as ls shows."
)
@click.option(
    "--file",
    "-f", type=click.STRING,
    required=True,
    help="file/folder path."
)
def rm(bucket, file):
    token = _feastToken()
    if not token:
        click.echo("Need login first.")
        return
    token = str(token)
    try:
        bucket = Bucket(bucket, User(token))
        bucket.remove([
            bucket.File(
                name=str(file).strip("/").split("/")[-1] + ("/" if str(file).endswith("/") else ""),
                _type="folder" if str(file).endswith("/") else "file",
                path="/".join(str(file).strip("/").split("/")[:-1]) + "/"
            )
        ])
    except AssertionError:
        click.echo("Something went wrong, please check the args.")
        click.echo("at Bucket.Create/Bucket.Remove")
        return


@main.command(
    help="As mkdir in linux. Make a directory."
)
@click.option(
    "--bucket",
    "-b", type=click.STRING,
    required=True,
    help="bucket name as same as ls shows."
)
@click.option(
    "--fullpath",
    "-fp", type=click.STRING,
    required=True,
    help="folder path from the / of the bucket."
)
def mkdir(bucket, fullpath):
    token = _feastToken()
    if not token:
        click.echo("Need login first.")
        return
    token = str(token)

    fullpath = str(fullpath).strip("/").strip()

    try:
        bucket = Bucket(bucket, User(token))
        bucket.mkdir(fullpath)
    except AssertionError:
        click.echo("Something went wrong, please check the args.")
        click.echo("at Bucket.Create/Bucket.Mkdir")
        return


def _feastToken():
    # Config file doesn't exist
    if not os.path.exists("./config.json"):
        return False

    # Read and parse config, overwritten to blank if failed
    try:
        config = json.loads(open("./config.json", "r").read())
    except Exception:
        open("./config.json", "w").write("")
        click.echo("Config file crashed, overwritten.")
        return False

    # Config parsed but actually no token there.
    if config == {}:
        return False

    # Token is invalid.
    if requests.get(
            url="https://api.dogecloud.com/console/index.json",
            params={"product": "home"},
            cookies={"token": config["token"]},
            headers={"authorization": "COOKIE"}
    ).json()["code"] != 200:
        return False

    return config["token"]


def _progress(bar: tqdm, message, progress):
    bar.update(progress - bar.n)
    bar.set_postfix(etag=message)


@main.command(
    help="Show version of Peg.",
)
def version():
    click.echo("0.1~Peg~Code by LemonPrefect with love, me@lemonprefect.cn")


if __name__ == "__main__":
    main()
