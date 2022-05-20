import json
import logging
import os
import time
import urllib.parse
from pathlib import Path
import click
import httpx as requests
from tqdm import tqdm

from cli.core.Exception import CliRequestError, CliException
from cli.core.utilities.PathUtils import NormalizePath, KeySplit
from cli.core.helpers import LoginHelper
from cli.core.User import User
from cli.core.Bucket import Bucket
from cli.core.File import File
from cli.core.uploader.CosUploader import CosUploader

logger = logging.getLogger(__name__)


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

    file = Path(file)
    if os.path.isdir(file):
        rootDirAbsPath = NormalizePath(file.absolute().as_posix())

        # find all the files recursively, get the path based on the uploading folder(not including) and filename.
        files = [(
            _file.absolute().as_posix().rpartition(_file.name)[0].partition(rootDirAbsPath)[2],
            _file.name
        ) for _file in file.resolve().glob('**/*') if _file.is_file()]

        # if --no-root-folder not enabled, append the folder name to the upload path.
        # selfDirPath = NormalizePath(Path(file).resolve().name)
    else:
        # fallback single file to merge the upload action
        rootDirAbsPath = NormalizePath(file.absolute().parent.as_posix())
        files = [("", file.name)]

    path = NormalizePath(path)
    # Apply for upload info
    response = bucket.session.post(
        url="/upload/auth.json",
        json={
            "scope": f"{bucket.name}:{path}*",
            "deadline": round(time.time()) + 10000  # 2 hours to upload a folder, maybe enough.
        }
    )
    data = response.json()
    logger.debug(response.request)
    logger.debug(data)
    if response.status_code != 200 or data.get("code", 0) != 200:
        click.echo("Upload token failed.")

    sessionToken, accessKeyId, secretAccessKey, info = tuple(data["data"]["uploadToken"].split(":"))
    bucket.setUploader(CosUploader(sessionToken, accessKeyId, secretAccessKey, info))

    if not files:
        click.echo(f"No files in the folder {rootDirAbsPath}")
        return

    for localPath, filename in files:
        uploadPath = f"{path}/{localPath}"
        bar = tqdm(total=100, ncols=120, desc=filename, ascii=True)
        try:
            bucket.upload(
                file=File(
                    name=filename,
                    path=NormalizePath(Path(os.path.join(file, localPath)).absolute().as_posix())
                    if localPath != ""
                    else NormalizePath(file.parent.absolute().as_posix()),
                    _type="file"
                ),
                path=uploadPath,
                callbackProgress=lambda x, y: _progress(bar, progress=round(x / y * 100), message=None)
            )
            _progress(bar, progress=100, message=None)
        except CliException:
            click.echo("Something went wrong, please check the args.")
            click.echo("at Bucket.Upload")


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
    """
    List bucket or file in bucket like ls
    :param bucket: bucket name, None if listing bucket
    :param path: path from the root of bucket to be list, None if listing bucket
    :return: None
    """
    token = _feastToken()
    if not token:
        click.echo("Need login first.")
        return
    token = str(token)

    if not bucket:
        response = requests.get(
            url="https://api.dogecloud.com/oss/bucket/list.json",
            cookies={"token": token},
            headers={"authorization": "COOKIE"}
        )

        data = response.json()
        logger.debug(response.request)
        logger.debug(data)
        if response.status_code != 200 or data.get("code") != 200:
            raise CliRequestError(response)

        click.echo(f"{'id':<10}\t{'name':<30}\t{'stored'}")
        for bucket in data.get("data", {}).get("buckets", {}):
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
        click.echo(
            f"{file.name.replace(path if path.endswith('/') else (path + '/'), ''):<60}\t"
            f"{(int(file.fileSize) / 1024):.2f} KiB"
        )


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
    """
    Login and save token
    :param method: login method whthin vcode or password
    :param phone: phone number represents an account
    :return: None
    """
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
    """
    Logout and remove the token
    :return: None
    """
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
    """
    Move file from src to dst
    :param bucket: bucket name
    :param src: source directory in the bucket
    :param dst: destination directory in the bucket
    :return: None
    """

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
        path, name = KeySplit(file)
        name = NormalizePath(name) if str(file).endswith("/") else name
        bucket.remove([
            File(
                name=name,
                _type="folder" if name.endswith("/") else "file",
                path=NormalizePath(path).lstrip("/")
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
    """
    Make a directory in the bucket.
    :param bucket: bucket name
    :param fullpath: fullpath from root of the bucket, directory name needed
    :return: None
    """
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
    except FileNotFoundError or ValueError:
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
    ).json().get("code", 0) != 200:
        return False

    return config["token"]


def _progress(bar: tqdm, message, progress):
    bar.update(progress - bar.n)
    bar.set_postfix(etag=message)


@main.command(
    help="Show version of Peg.",
)
def version():
    click.echo("0.2~Peg~Code by LemonPrefect with love, me@lemonprefect.cn")


if __name__ == "__main__":
    main()
