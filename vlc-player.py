#!/usr/bin/python3

import logging
import os
import sys
import threading
import uuid
from concurrent import futures
from typing import Optional, Callable, Any, Iterable, Mapping

import vlc
from main import DbCon
import tempfile
from main import MediaEncrypt

# os.environ['PYTHON_VLC_MODULE_PATH'] = "C:\Program Files\VideoLAN\VLC"

logging.basicConfig(level=logging.DEBUG)

class VlcPlayer:
    '''
        args:设置 options
    '''
    def __init__(self, *args):
        if args:
            instance = vlc.Instance(*args)
            self.media = instance.media_player_new()
        else:
            self.media = vlc.MediaPlayer()

    # 设置待播放的url地址或本地文件路径，每次调用都会重新加载资源
    def set_uri(self, uri):
        self.media.set_mrl(uri)

    # 播放 成功返回0，失败返回-1
    def play(self, path=None):
        if path:
            self.set_uri(path)
            return self.media.play()
        else:
            return self.media.play()

    # 暂停
    def pause(self):
        self.media.pause()

    # 恢复
    def resume(self):
        self.media.set_pause(0)

    # 停止
    def stop(self):
        self.media.stop()

    # 释放资源
    def release(self):
        return self.media.release()

    # 是否正在播放
    def is_playing(self):
        return self.media.is_playing()

    # 已播放时间，返回毫秒值
    def get_time(self):
        return self.media.get_time()

    # 拖动指定的毫秒值处播放。成功返回0，失败返回-1 (需要注意，只有当前多媒体格式或流媒体协议支持才会生效)
    def set_time(self, ms):
        return self.media.get_time()

    # 音视频总长度，返回毫秒值
    def get_length(self):
        return self.media.get_length()

    # 获取当前音量（0~100）
    def get_volume(self):
        return self.media.audio_get_volume()

    # 设置音量（0~100）
    def set_volume(self, volume):
        return self.media.audio_set_volume(volume)

    # 返回当前状态：正在播放；暂停中；其他
    def get_state(self):
        state = self.media.get_state()
        if state == vlc.State.Playing:
            return 1
        elif state == vlc.State.Paused:
            return 0
        else:
            return -1

    # 当前播放进度情况。返回0.0~1.0之间的浮点数
    def get_position(self):
        return self.media.get_position()

    # 拖动当前进度，传入0.0~1.0之间的浮点数(需要注意，只有当前多媒体格式或流媒体协议支持才会生效)
    def set_position(self, float_val):
        return self.media.set_position(float_val)

    # 获取当前文件播放速率
    def get_rate(self):
        return self.media.get_rate()

    # 设置播放速率（如：1.2，表示加速1.2倍播放）
    def set_rate(self, rate):
        return self.media.set_rate(rate)

    # 设置宽高比率（如"16:9","4:3"）
    def set_ratio(self, ratio):
        self.media.video_set_scale(0)  # 必须设置为0，否则无法修改屏幕宽高
        self.media.video_set_aspect_ratio(ratio)

    # 注册监听器
    def add_callback(self, event_type, callback):
        self.media.event_manager().event_attach(event_type, callback)

    # 移除监听器
    def remove_callback(self, event_type, callback):
        self.media.event_manager().event_detach(event_type, callback)


class Player:
    db = None
    vlc_player = None
    name = None
    log = None

    def __init__(self, player=VlcPlayer(), db_path="meta.db"):
        self.vlc_player = player
        self.db = DbCon(db_path)
        self.name = str(uuid.uuid1())
        self.log = logging.getLogger("player-" + self.name)

    def get_source_file_name(self, media_path: str):
        return media_path.split(os.sep)[-1]

    def get_source_file_suffix(self, source_file_name):
        return self.get_source_file_meta(source_file_name)[1]

    def get_source_file_meta(self, source_file_name):
        return self.db.get_meta_by_new_name(source_file_name)

    def decode(self, media_path, key):
        class DecodeThread(threading.Thread):

            db = None
            dest_file = None
            source_file = None
            key = None

            def __init__(self, db, dest_file, source_file, key):
                super().__init__()
                self.db = db
                self.dest_file = dest_file
                self.source_file = source_file
                self.key = key

            def run(self):
                decoder = MediaEncrypt(self.db)
                decoder.decrypt_file(self.key, self.source_file, self.dest_file, 1024 * 512)

        tf = tempfile.NamedTemporaryFile('w+b')
        futures.Executor()
        decode_thread = DecodeThread(self.db, tf.name, media_path, key)
        decode_thread.start()
        # decode_thread.join()
        return tf.name

    def play_encoded_media(self, encoded_media_path, key):
        decoded_media_path = self.decode(encoded_media_path, key)
        self.play(decoded_media_path)

    def play(self, media_path):
        def my_call_back(event):
            print("call:", self.vlc_player.get_time())

        self.vlc_player.add_callback(vlc.EventType.MediaPlayerTimeChanged, my_call_back)
        # 在线播放流媒体视频
        self.log.debug("playing {}".format(media_path))
        print(media_path)
        r = self.vlc_player.play(media_path)
        if not r == 0:
            self.log.debug("can't play {}".format(media_path))
        print(r)

        os.system("pause")


if __name__ == '__main__':
    media_path = sys.argv[1]
    key = sys.argv[2]
    player = Player()
    player.play("xxx")
    # player.play_encoded_media(media_path, key)
