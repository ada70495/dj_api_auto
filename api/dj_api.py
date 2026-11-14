"""DJ 音乐播放器接口：歌单、播放、暂停、切歌、音量、均衡器、播放模式"""


class DjApi:
    def __init__(self, client):
        self.client = client

    def playlist(self):
        return self.client.get("/dj/playlist")

    def play(self, song_id: int):
        return self.client.post("/dj/play", json={"song_id": song_id})

    def pause(self):
        return self.client.post("/dj/pause")

    def next_song(self):
        return self.client.post("/dj/next")

    def prev_song(self):
        return self.client.post("/dj/prev")

    def volume(self, volume: int):
        return self.client.post("/dj/volume", json={"volume": volume})

    def eq(self, mode: str):
        return self.client.post("/dj/eq", json={"mode": mode})

    def play_mode(self, mode: str):
        return self.client.post("/dj/play_mode", json={"mode": mode})
