#!/usr/bin/python3
from webapp.api import app  # Replace 'your_app_name' with the name of your FastAPI app file
from fastapi.testclient import TestClient
import fastapi.security
import httpx
import tomllib
import asyncio
import pytest
import logging
from webapp.executor import Executor
from webapp.config import Config
from webapp.challenge import Challenge

CONFIG_PATH = "config.toml"

def get_config():
    with open(CONFIG_PATH, "rb") as config:
        data = tomllib.load(config)
    return data

def get_authentication():
    config = get_config()
    return httpx.BasicAuth(config["api"]["username"], config["api"]["password"])

client = TestClient(app)
config = Config(CONFIG_PATH)
executor = Executor(config)
pytest_plugins = ('pytest_asyncio',)

asyncio.run(executor.create_enviroment())

app.extra = {
    "config": config,
    "executor": executor
}

def test_start_stop_status_endpoints(): 
    user_id = "12345"  # Arbitrary user ID
    service_name = "buffer_overflow"
    
    auth = get_authentication()
    
    response = client.get(f"/start/{user_id}/{service_name}", auth=auth)
    print(f"Instancer responded with {response.content}")
    assert response.status_code == 200

    response = client.get(f"/status/{user_id}/{service_name}", auth=auth)
    print(f"Instancer responded to status with {response.content}")
    assert response.status_code == 200
    
    response = client.get(f"/stop/{user_id}/{service_name}", auth=auth)
    print(f"Instancer responded to stop with {response.content}")
    assert response.status_code == 200

async def start_challenge(uuid, name, app):
    executor = app.extra["executor"]
    challenge = app.extra["config"].challenges[name]
    
    if await challenge.working_set.contains_or_insert(uuid):
        await challenge.start(executor, uuid)

async def stop_challenge(uuid, name, app):
    executor = app.extra["executor"]
    challenge = app.extra["config"].challenges[name]
    
    await challenge.stop(executor, uuid)

def assert_challenge_status(uuid, name, expected_result):
    auth = get_authentication()
    response = client.get(f"/status/{uuid}/{name}", auth=auth)
    print(f"Instancer responded to status with {response.content}")
    assert response.status_code == 200
    assert response.content == expected_result

@pytest.mark.asyncio
async def test_start_instance(caplog):
    user_id = "1234"
    challenge_name = "buffer_overflow"

    caplog.set_level(logging.INFO)

    assert_challenge_status(user_id, challenge_name, b'{"state":"stopped"}')

    await start_challenge(user_id, challenge_name, app)
    assert_challenge_status(user_id, challenge_name,  b'{"state":"started"}')
    
    await stop_challenge(user_id, challenge_name, app)
    assert_challenge_status(user_id, challenge_name, b'{"state":"stopped"}')

@pytest.mark.asyncio
async def test_restart_instance(caplog):
    user_id = "1234"
    challenge_name = "buffer_overflow"
    caplog.set_level(logging.INFO)
    
    for i in range(0,2):

        await start_challenge(user_id, challenge_name, app)
        assert_challenge_status(user_id, challenge_name,  b'{"state":"started"}')
        
        await stop_challenge(user_id, challenge_name, app)
        assert_challenge_status(user_id, challenge_name, b'{"state":"stopped"}')

@pytest.mark.asyncio
async def test_start_two_challs(caplog):
    caplog.set_level(logging.INFO)
    
    user_ids = ["1000", "2000"]
    challenge_name = "buffer_overflow"

    for user_id in user_ids:
        assert_challenge_status(user_id, challenge_name, b'{"state":"stopped"}')
        await start_challenge(user_id, challenge_name, app)
        assert_challenge_status(user_id, challenge_name,  b'{"state":"started"}')
    
    for user_id in user_ids:
        
        assert_challenge_status(user_id, challenge_name, b'{"state":"started"}')
        await stop_challenge(user_id, challenge_name, app)
        assert_challenge_status(user_id, challenge_name, b'{"state":"stopped"}')

# some negative tests
@pytest.mark.asyncio
async def test_nonexistent_challenge(caplog):
    user_id = "1234"
    challenge_name = "43986751345136903146"
    expected_msg = bytes(f'["Challenge \'{challenge_name}\' not found"]', encoding='utf8')
    caplog.set_level(logging.INFO)
    auth = get_authentication()

    response = client.get(f"/start/{user_id}/{challenge_name}", auth=auth)
    assert response.content == expected_msg
    assert response.status_code == 200

    assert_challenge_status(user_id, challenge_name, expected_msg)
    
    response = client.get(f"/stop/{user_id}/{challenge_name}", auth=auth)
    assert response.content == expected_msg
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_stopping_stopped_challenge(caplog):
    user_id = "1234"
    challenge_name = "buffer_overflow"
    caplog.set_level(logging.INFO)
    auth = get_authentication()
    
    response = client.get(f"/stop/{user_id}/{challenge_name}", auth=auth)
    assert response.content == b'["not running"]'
    assert response.status_code == 200
    
    assert_challenge_status(user_id, challenge_name, b'{"state":"stopped"}')

@pytest.mark.asyncio
async def test_starting_started_challenge(caplog):
    user_id = "1234"
    challenge_name = "buffer_overflow"
    caplog.set_level(logging.INFO)

    assert_challenge_status(user_id, challenge_name, b'{"state":"stopped"}')

    await start_challenge(user_id, challenge_name, app)
    assert_challenge_status(user_id, challenge_name,  b'{"state":"started"}')
    
    await start_challenge(user_id, challenge_name, app)
    assert_challenge_status(user_id, challenge_name, b'{"state":"started"}')

    await stop_challenge(user_id, challenge_name, app)
    assert_challenge_status(user_id, challenge_name, b'{"state":"stopped"}')
















