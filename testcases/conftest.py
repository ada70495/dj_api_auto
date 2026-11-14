"""全局 fixture：请求客户端、登录、数据复位"""
import os
import sys

import pytest

# 保证从任意目录运行都能 import 项目内的包
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from common.conf_handler import config
from common.logger_handler import logger
from common.request_handler import RequestHandler


@pytest.fixture(scope="session")
def client() -> RequestHandler:
    """全 session 共用一个 Session 和一个 token"""
    c = RequestHandler()
    logger.info(f"测试环境：{config.summary()}")
    yield c
    c.close()


@pytest.fixture(scope="session", autouse=True)
def prepared_env(client):
    """环境自愈：复位 Mock 数据 → 登录

    歌单是服务端的固定数据，不需要额外预置；
    播放状态每条用例自行设置，避免用例之间互相依赖。
    """
    logger.info("=== 测试环境准备开始 ===")

    resp = client.post("/__admin/reset")
    assert resp.json()["code"] == 200, "Mock 服务复位失败，请确认 mock_server 已启动且地址正确"

    login_data = client.login()
    assert login_data.get("token") or login_data.get("data", {}).get("token"), f"登录失败：{login_data}"

    logger.info("=== 测试环境准备结束 ===")
    yield
