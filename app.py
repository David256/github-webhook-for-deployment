import os
import hashlib
import hmac
import json
import logging
import pathlib
import asyncio
from typing import Union
from distutils.version import StrictVersion
from fastapi import FastAPI, Header, Request, HTTPException, status
from fastapi.requests import Request
from fastapi.middleware.cors import CORSMiddleware


SECRET_TOKEN = os.environ.get('SECRET_TOKEN')
if SECRET_TOKEN is None:
    raise RuntimeError('The SECRET_TOKEN environment variable is empty.')


GIT_PATH = os.environ.get('GIT_PATH')
if GIT_PATH is None:
    raise RuntimeError('The GIT_PATH environment variable is empty.')


app = FastAPI()
log_handler = logging.StreamHandler()
log_format = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
log_handler.setFormatter(log_format)
LOG = logging.getLogger('GHWHOOK')
LOG.addHandler(log_handler)
LOG.setLevel(logging.DEBUG)

origins = ['*']
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
LOG.info('will watch %s', GIT_PATH)


def check_signature(data: bytes, signature_256: str) -> bool:
    """Check if the signature matches with the data.

    Args:
        data (bytes): The data body.
        signature_256 (str): The sent signature.

    Returns:
        bool: True if it matches; otherwise False.
    """
    _hmac = hmac.new(
        SECRET_TOKEN.encode('utf-8'),
        msg=data,
        digestmod=hashlib.sha256,
    )
    _hash = _hmac.hexdigest()
    LOG.info('check signature: %s == %s?', _hash, signature_256)
    return hmac.compare_digest(_hash, signature_256)


async def get_local_tags(path: Union[pathlib.Path, str]) -> list[str]:
    """Get the git tags from given git directory path.

    Args:
        path (Union[pathlib.Path, str]): The GIT directory path.

    Returns:
        list[str]: tag list.
    """
    if isinstance(path, str):
        path = pathlib.Path(path)
    abs_path = path.absolute()
    LOG.info('check tags in path %s', abs_path)

    # Ask for the tags
    process = await asyncio.create_subprocess_exec(
        'git',
        '-C',
        abs_path,
        '--no-pager',
        'tag',
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await process.wait()
    stdout, stderr = await process.communicate()
    LOG.debug('stdout: %s', stdout)
    LOG.debug('stderr: %s', stderr)

    if stderr:
        LOG.error(stderr.decode())
        return []
    elif stdout is None:
        LOG.error('stdout is none')
        return []

    lines = stdout.decode().split('\n')
    lines = [line.strip() for line in lines if line.strip()]

    versions = []
    for line in lines:
        try:
            versions.append(StrictVersion(line))
        except ValueError as e:
            LOG.error('cannot parse version "%s": %s' % (line, e))

    versions.sort()
    tabs = [str(version) for version in versions]
    LOG.debug(tabs[-10:])
    return tabs


@app.post('/')
async def payload(
    request: Request,
    x_gitHub_event: str = Header(...),
    # x_hub_signature: str = Header(...),
    x_hub_signature_256: str = Header(...),
):
    data = await request.body()

    try:
        sha_256_name, signature_256 = x_hub_signature_256.split('=')
        if sha_256_name != 'sha256':
            raise ValueError('Bad HTTP header value: %s' % x_hub_signature_256)
    except ValueError as e:
        LOG.error(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Misunderstandable "{x_hub_signature_256}"',
        )

    if not check_signature(data, signature_256):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Bad signature po',
        )

    if x_gitHub_event != 'create':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Unwanted event "{x_gitHub_event}"',
        )

    obj = json.loads(data)
    ref = obj['ref']
    sender = obj['sender']
    login_sender = sender['login']
    LOG.info('%s calls %s %s', login_sender, x_gitHub_event, ref)

    # Check if should do git pull
    tabs = await get_local_tags(pathlib.Path(GIT_PATH))
    
    if len(tabs) != 0 and tabs[-1] != ref:
        LOG.info('update from %s to %s', tabs[-1], ref)
    else:
        LOG.info('found same tag: %s and %s', tabs[-1], ref)
        return { 'info': f'The last tag is the same: {tabs[-1]}' }
    
    # Update
    LOG.info('update to tag %s', ref)
    return { 'info': f'update to {ref}' }
