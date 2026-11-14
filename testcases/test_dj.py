"""DJ 音乐播放器：歌单查询、播放、暂停、切歌、音量、均衡器、播放模式"""
import os

import allure
import pytest
import yaml

from api.dj_api import DjApi
from common.assert_handler import AssertHandler

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

with open(os.path.join(DATA_DIR, "dj_data.yaml"), "r", encoding="utf-8") as _f:
    DJ = yaml.safe_load(_f)


@allure.feature("DJ 音乐播放器")
class TestDjApi:

    @allure.story("查询歌单")
    def test_playlist(self, client):
        resp = DjApi(client).playlist()
        body = resp.json()

        a = AssertHandler()
        a.eq(body["code"], 200, "业务码")
        a.eq(body["data"]["total"], len(body["data"]["list"]), "total 与列表长度一致")
        a.gt(body["data"]["total"], 0, "歌曲总数")
        for song in body["data"]["list"]:
            a.contains(song, "song_id", "歌曲字段 song_id")
            a.not_none(song.get("name"), "歌曲名称")
            a.gt(song.get("duration", 0), 0, "歌曲时长")
        a.finish()

    @allure.story("播放歌曲")
    @pytest.mark.parametrize("case", DJ["play_cases"], ids=lambda c: c["case_name"])
    def test_play(self, client, case):
        resp = DjApi(client).play(case["song_id"])
        body = resp.json()

        a = AssertHandler()
        a.eq(body["code"], case["expect"]["code"], "业务码")
        if body["code"] == 200:
            a.eq(body["data"]["song_id"], case["song_id"], "播放的歌曲ID")
            a.eq(body["data"]["playing"], True, "播放状态")
            a.gt(body["data"]["duration"], 0, "歌曲时长")
        else:
            a.contains(body["msg"], case["expect"]["msg"], "错误提示")
        a.finish()

    @allure.story("暂停播放")
    def test_pause(self, client):
        dj = DjApi(client)
        dj.play(1)

        resp = dj.pause()
        body = resp.json()

        a = AssertHandler()
        a.eq(body["code"], 200, "业务码")
        a.eq(body["data"]["playing"], False, "暂停后播放状态")
        a.eq(body["data"]["song_id"], 1, "暂停后仍指向当前歌曲")
        a.finish()

    @allure.story("未播放时暂停")
    def test_pause_without_playing(self, client):
        client.post("/__admin/reset")

        resp = DjApi(client).pause()
        body = resp.json()

        a = AssertHandler()
        a.eq(body["code"], 400, "业务码")
        a.contains(body["msg"], "没有正在播放", "错误提示")
        a.finish()

    @allure.story("切换到下一首")
    def test_next_song(self, client):
        dj = DjApi(client)
        dj.play(1)

        resp = dj.next_song()
        body = resp.json()

        a = AssertHandler()
        a.eq(body["code"], 200, "业务码")
        a.eq(body["data"]["song_id"], 2, "应切到第二首")
        a.eq(body["data"]["playing"], True, "切歌后处于播放状态")
        a.finish()

    @allure.story("未播放时切下一首")
    def test_next_without_playing(self, client):
        client.post("/__admin/reset")

        resp = DjApi(client).next_song()
        body = resp.json()

        a = AssertHandler()
        a.eq(body["code"], 400, "业务码")
        a.contains(body["msg"], "没有正在播放", "错误提示")
        a.finish()

    @allure.story("切换到上一首")
    def test_prev_song(self, client):
        dj = DjApi(client)
        dj.play(2)

        resp = dj.prev_song()
        body = resp.json()

        a = AssertHandler()
        a.eq(body["code"], 200, "业务码")
        a.eq(body["data"]["song_id"], 1, "应切回第一首")
        a.eq(body["data"]["playing"], True, "切歌后处于播放状态")
        a.finish()

    @allure.story("首曲向前切时循环到末曲")
    def test_prev_song_from_first(self, client):
        dj = DjApi(client)
        dj.play(1)

        resp = dj.prev_song()
        body = resp.json()

        a = AssertHandler()
        a.eq(body["code"], 200, "业务码")
        a.eq(body["data"]["song_id"], len(DjApi(client).playlist().json()["data"]["list"]), "应循环到最后一首")
        a.finish()

    @allure.story("设置音量")
    @pytest.mark.parametrize("case", DJ["volume_cases"], ids=lambda c: c["case_name"])
    def test_volume(self, client, case):
        resp = DjApi(client).volume(case["volume"])
        body = resp.json()

        a = AssertHandler()
        a.eq(body["code"], case["expect"]["code"], "业务码")
        if body["code"] == 200:
            a.eq(body["data"]["volume"], case["volume"], "音量已生效")
        else:
            a.contains(body["msg"], case["expect"]["msg"], "错误提示")
        a.finish()

    @allure.story("切换均衡器")
    @pytest.mark.parametrize("case", DJ["eq_cases"], ids=lambda c: c["case_name"])
    def test_eq(self, client, case):
        resp = DjApi(client).eq(case["mode"])
        body = resp.json()

        a = AssertHandler()
        a.eq(body["code"], case["expect"]["code"], "业务码")
        if body["code"] == 200:
            a.eq(body["data"]["mode"], case["mode"], "均衡器已生效")
        else:
            a.contains(body["msg"], case["expect"]["msg"], "错误提示")
        a.finish()

    @allure.story("切换播放模式")
    @pytest.mark.parametrize("case", DJ["play_mode_cases"], ids=lambda c: c["case_name"])
    def test_play_mode(self, client, case):
        resp = DjApi(client).play_mode(case["mode"])
        body = resp.json()

        a = AssertHandler()
        a.eq(body["code"], case["expect"]["code"], "业务码")
        if body["code"] == 200:
            a.eq(body["data"]["mode"], case["mode"], "播放模式已生效")
        else:
            a.contains(body["msg"], case["expect"]["msg"], "错误提示")
        a.finish()
