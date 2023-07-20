#!/usr/bin/python3
import datetime
import logging
import os
import re
import shutil
import sqlite3
import sys
import uuid
from logging.handlers import TimedRotatingFileHandler

import browser_cookie3
import ffmpeg
import psutil
from pybaiduphoto import API as YiKeAPI

# logging.basicConfig(filename="./logs/main.log", level=logging.INFO)
# log = logging.getLogger("main")

if not os.path.exists("./logs"):
    os.mkdir("./logs")
log_handle = TimedRotatingFileHandler("./logs/main.log", when="D")
console_log_handle = logging.StreamHandler()
console_log_handle.setLevel(logging.INFO)
log = logging.getLogger("main")
log.setLevel(logging.INFO)
log.addHandler(log_handle)
log.addHandler(console_log_handle)

table_ddl_meta = """
CREATE TABLE "meta_info" (
	"id"	INTEGER NOT NULL UNIQUE COLLATE BINARY,
	"source_name"	TEXT NOT NULL,
	"new_name"	TEXT NOT NULL,
	"size"	INTEGER NOT NULL,
	"date"	TEXT NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT)
);
"""

table_ddl_split_file_info = """
CREATE TABLE "split_file_info" (
	"id"	INTEGER NOT NULL UNIQUE,
	"source_name"	TEXT NOT NULL,
	"new_name"	TEXT NOT NULL,
	"size"	INTEGER NOT NULL,
	"date"	TEXT NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT)
);
"""

table_ddl_split_file_info_mpeg = """
CREATE TABLE "split_file_info_mpeg" (
	"id"	INTEGER NOT NULL UNIQUE,
	"source_name"	TEXT NOT NULL,
	"new_name"	TEXT NOT NULL,
	"size"	INTEGER NOT NULL,
	"date"	TEXT NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT)
);
"""

table_ddl_split_file_info_translate = """
CREATE TABLE "split_file_info_translate" (
	"id"	INTEGER NOT NULL UNIQUE,
	"source_name"	TEXT NOT NULL,
	"new_name"	TEXT NOT NULL,
	"size"	INTEGER NOT NULL,
	"date"	TEXT NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT)
);
"""

class DbCon:

    con = None
    db_path = None

    def __init__(self, db_path="meta.db"):
        self.db_path = db_path
        self.get_db_con()

    def __del__(self):
        self.con.close()

    def init_meta_db(self):
        cursor = self.con.cursor()
        cursor.execute(table_ddl_meta)
        cursor.execute(table_ddl_split_file_info)
        cursor.execute(table_ddl_split_file_info_mpeg)
        cursor.close()
        self.con.commit()

    def insert_meta(self, source_name, new_name, file_size, date):
        cursor = self.con.cursor()
        cursor.execute("insert into meta_info (source_name, new_name, `size`, `date`) values (?, ?, ?, ?)", (source_name, new_name, file_size, date))
        cursor.close()
        self.con.commit()

    def get_meta_by_new_name(self, new_name):
        cursor = self.con.cursor()
        cursor.execute("select * from meta_info where new_name=?", (new_name, ))
        return cursor.fetchone()

    def list_meta_all(self):
        cursor = self.con.cursor()
        cursor.execute("select * from meta_info")
        return cursor.fetchall()

    def get_last_row_id(self) -> int:
        cursor = self.con.cursor()
        cursor.execute("SELECT  MAX(id) FROM meta_info")
        return cursor.fetchone()[0]

    def list_meta_by_source_name_index_for_one_video(self, source_name: str):
        query_name = re.sub(r"(?<=\.).(?=\.)", "%", source_name)
        cursor = self.con.cursor()
        cursor.execute("select * from meta_info mi where source_name like ?", (query_name, ))
        return cursor.fetchall()

    def list_meta_by_source_name_prefix_for_one_video(self, source_name: str):
        cursor = self.con.cursor()
        cursor.execute("select * from meta_info mi where source_name like ?", (source_name + "%", ))
        return cursor.fetchall()

    #
    #        split_file_info
    #

    def insert_split_file_info(self, source_name, new_name, file_size, date):
        cursor = self.con.cursor()
        cursor.execute("insert into split_file_info (source_name, new_name, `size`, `date`) values (?, ?, ?, ?)", (source_name, new_name, file_size, date))
        cursor.close()
        self.con.commit()

    def get_split_file_info_by_source_name(self, source_name) -> list:
        cursor = self.con.cursor()
        cursor.execute("select * from split_file_info where source_name=?", (source_name, ))
        return cursor.fetchone()

    def insert_split_file_info_mpeg(self, source_name, new_name, file_size, date):
        cursor = self.con.cursor()
        cursor.execute("insert into split_file_info_mpeg (source_name, new_name, `size`, `date`) values (?, ?, ?, ?)", (source_name, new_name, file_size, date))
        cursor.close()
        self.con.commit()

    def get_split_file_info_by_source_name_mpeg(self, source_name) -> list:
        cursor = self.con.cursor()
        cursor.execute("select * from split_file_info_mpeg where source_name=?", (source_name,))
        return cursor.fetchone()

    def insert_split_file_info_translate(self, source_name, new_name, file_size, date):
        cursor = self.con.cursor()
        cursor.execute("insert into split_file_info_translate (source_name, new_name, `size`, `date`) values (?, ?, ?, ?)", (source_name, new_name, file_size, date))
        cursor.close()
        self.con.commit()

    def get_split_file_info_by_source_name_translate(self, source_name) -> list:
        cursor = self.con.cursor()
        cursor.execute("select * from split_file_info_translate where source_name=?", (source_name,))
        return cursor.fetchone()

    def get_db_con(self):
        if self.con is not None:
            return self.con
        self.con = sqlite3.connect(self.db_path, check_same_thread=False)
        cursor = self.con.cursor()
        try:
            cursor.execute("select * from meta_info;")
            cursor.close()
        except Exception as e:
            log.info("meta db not found. init it.")
            cursor.close()
            self.init_meta_db()
        else:
            return self.con

    def get_meta_by_new_name_group(self, group_name):
        cursor = self.con.cursor()
        cursor.execute("select * from meta_info where new_name like '{}#%'".format(group_name))
        return cursor.fetchall()


class MediaEncrypt:

    con: DbCon = None

    def __init__(self, con):
        self.con = con

    def encrypt_xor(self, bytes, key_bytes):
        if len(key_bytes) > 1:
            raise ValueError("key bytes must be one num");
        ret = bytearray()
        for b in bytes:
            ret.append(b ^ key_bytes[0])
        return ret

    def decrypt_xor(self, bytes, key_bytes):
        return self.encrypt_xor(bytes, key_bytes)

    def encrypt_file(self, key, file, output_file, chunk_size=1024 * 1024 * 100):
        with open(file, "rb") as f, open(output_file, "wb") as of:
            chuck_block = f.read(chunk_size)
            while chuck_block:
                out_chuck = self.encrypt_xor(chuck_block, bytes(key, "u8"))
                of.write(out_chuck)
                chuck_block = f.read(chunk_size)

    def decrypt_file(self, key, file, output_file, chunk_size=1024 * 1024 * 100):
        if os.path.exists(output_file):
            log.info("file {} already exitst.".format(output_file))
            return
        self.encrypt_file(key, file, output_file, chunk_size)

    # departed
    def anonymous_filename(self, source_name, file_size):
        new_name = str(uuid.uuid1())
        self.con.insert_meta(source_name, new_name, file_size, datetime.datetime.now())
        return new_name

    # departed
    def anonymous_filename_with_subfix(self, source_name: str, file_size):
        new_name = ".".join([str(uuid.uuid1()), source_name.split(".")[-1]])
        self.con.insert_meta(source_name, new_name, file_size, datetime.datetime.now())
        return new_name

    def anonymous_filename_by_group(self, source_name, file_size, group_name: str):
        new_name = str(group_name) + "#" + str(uuid.uuid1())
        self.con.insert_meta(source_name, new_name, file_size, datetime.datetime.now())
        return new_name

    def anonymous_filename_with_subfix_by_group(self, source_name: str, file_size: int, group_name: str):
        new_name = str(group_name) + "#" + ".".join([str(uuid.uuid1()), source_name.split(".")[-1]])
        self.con.insert_meta(source_name, new_name, file_size, datetime.datetime.now())
        return new_name

    def get_last_row(self) -> int:
        return self.con.get_last_row_id()

    def get_real_filename(self, anonymous_name):
        meta_row = self.con.get_meta_by_new_name(anonymous_name)
        if meta_row is None:
            return None
        return meta_row[1]

    def encrypt_files(self, key, dir_path, dest_dir_path):
        if not os.path.exists(dest_dir_path):
            os.mkdir(dest_dir_path)
        dir = os.listdir(dir_path)
        for file in dir:
            file_path = os.path.join(dir_path, file)
            if not os.path.isfile(file_path):
                continue
            new_filename = self.anonymous_filename(file, os.path.getsize(file_path))
            log.info("start encrypting file {}".format(file))
            self.encrypt_file(key, file_path, os.path.join(dest_dir_path, new_filename))
            log.info("file {} encrypted.".format(file))

    def decrypt_files(self, key, dir_path, dest_dir_path):
        if not os.path.exists(dest_dir_path):
            os.mkdir(dest_dir_path)
        dir = os.listdir(dir_path)
        for file in dir:
            file_path = os.path.join(dir_path, file)
            if not os.path.isfile(file_path):
                continue
            new_filename = self.get_real_filename(file)
            if new_filename is None:
                log.info("file name {} not found in meta_table")
                continue
            log.info("start decrypting file {}".format(file))
            self.decrypt_file(key, file_path, os.path.join(dest_dir_path, new_filename))
            log.info("file {} decrypted.".format(file))

    def encrypt_files_with_subfix(self, key, dir_path, dest_dir_path):
        if not os.path.exists(dest_dir_path):
            os.mkdir(dest_dir_path)
        dir = os.listdir(dir_path)
        for file in dir:
            file_path = os.path.join(dir_path, file)
            if not os.path.isfile(file_path):
                continue
            new_filename_with_subfix = self.anonymous_filename_with_subfix(file, os.path.getsize(file_path))
            log.info("start encrypting file {}".format(file))
            self.encrypt_file(key, file_path, os.path.join(dest_dir_path, new_filename_with_subfix))
            log.info("file {} encrypted.".format(file))

    def encrypt_files_with_subfix_by_group(self, key, dir_path, dest_dir_path, group_name: str):
        if not os.path.exists(dest_dir_path):
            os.mkdir(dest_dir_path)
        dir = os.listdir(dir_path)
        for file in dir:
            file_path = os.path.join(dir_path, file)
            if not os.path.isfile(file_path):
                continue
            new_filename_with_subfix = self.anonymous_filename_with_subfix_by_group(file, os.path.getsize(file_path),
                                                                                    group_name)
            log.info("start encrypting file {}".format(file))
            self.encrypt_file(key, file_path, os.path.join(dest_dir_path, new_filename_with_subfix))
            log.info("file {} encrypted.".format(file))

    def get_all_real_filename_by_group(self, group_name):
        meta_row = self.con.get_meta_by_new_name_group(group_name)
        return meta_row

'''
文件拆分器，将一个文件拆分成指定大小的每一块。文件名同原文件_index
'''
class Spliter:

    db_con: DbCon = None
    max_size = None
    source_dir: str = None
    dest_dir: str = None

    def __init__(self, db_con, source_dir: str,  dest_dir: str, max_size: int):
        self.db_con = db_con
        self.max_size = max_size
        self.dest_dir = dest_dir
        self.source_dir = source_dir

    def split_file(self, file_name: str) -> list[str]:
        file = self.db_con.get_split_file_info_by_source_name(file_name)
        if file is not None:
            log.info("file {} already split.".format(file_name))
            return []
        origin_file_path = os.path.join(self.source_dir, file_name)
        if not check_disk_space(dest_dir, os.path.getsize(origin_file_path)):
            log.info("disk free space is low. stop. current filename {}".format(file_name))
            exit(1)
        file_num = (os.path.getsize(origin_file_path) // self.max_size) + 1
        new_filename_ary = []
        if file_num <= 1:
            log.info("file size is {} , lt max_size {}.".format(os.path.getsize(origin_file_path), self.max_size))
            new_filename_ary.append(file_name)
        else:
            log.info("file split to {} .".format(file_num))

            with open(origin_file_path, "rb") as f:
                origin_filename = file_name
                #for i in range(1, file_num):
                mb: bytes = f.read(self.max_size)
                i = 1
                while mb:
                    t_of_a: list = origin_filename.split(".")
                    t_of_a.insert(len(t_of_a) - 1, str(i))
                    new_filename: str = ".".join(t_of_a)
                    log.info("new file is {}. index {} for {}".format(new_filename, i, origin_filename))
                    new_file_path = os.path.join(self.dest_dir, new_filename)
                    log.info("new file path in {}".format(new_file_path))
                    with open(new_file_path, "wb") as nf:
                        result_w = nf.write(mb)
                        log.info("write result is {}".format(result_w))
                    mb = f.read(self.max_size)
                    i += 1
                    new_filename_ary.append(new_filename)
        self.db_con.insert_split_file_info(file_name, "#".join(new_filename_ary),
                                           os.path.getsize(origin_file_path), datetime.datetime.now())
        return new_filename_ary

    def split_dir(self, exclude: list):
        l_files = os.listdir(self.source_dir)
        for f_name in l_files:
            need_continue = False
            for ec in exclude:
                re_ec = re.compile(ec)
                res_s = re_ec.search(f_name)
                if res_s is not None:
                    log.info("cause by {}, pass {}".format(ec, f_name))
                    need_continue = True
                    break
            split_file_info = self.db_con.get_split_file_info_by_source_name(f_name)
            if split_file_info is not None:
                log.info("file {} already split.".format(f_name))
                need_continue = True
            if need_continue:
                continue
            self.split_file(f_name)

    ###
    # example param: ffmpeg -ss %d -t %d -accurate_seek -i %s -codec copy -avoid_negative_ts 1 %s
    ###
    def split_file_with_ffmpeg(self, file_name: str, duration: int, ffmpeg_param: str):
        file = self.db_con.get_split_file_info_by_source_name_mpeg(file_name)
        if file is not None:
            log.info("file {} already split.".format(file_name))
            return
        origin_file_path = os.path.join(self.source_dir, file_name)
        if not check_disk_space(self.dest_dir, os.path.getsize(origin_file_path)):
            log.info("disk free space is low. stop. current filename {}".format(file_name))
            exit(1)
        start_time = 0
        new_filename_ary = []
        media_duration = self.get_media_duration_time(origin_file_path)
        file_count_num = int(media_duration // duration) + 1
        if media_duration <= duration:
            log.info("media duration is {} , lt {}.".format(media_duration, duration))
            new_filename_ary.append(file_name)
        else:
            log.info("file split to {} .".format(file_count_num))
        for i in range(0, file_count_num):
            file_index = i + 1
            origin_filename = file_name
            t_of_a: list = origin_filename.split(".")
            t_of_a.insert(len(t_of_a) - 1, str(file_index))
            new_filename: str = ".".join(t_of_a)
            log.info("new file is {}. index {} for {}".format(new_filename, file_index, origin_filename))
            new_file_path = os.path.join(self.dest_dir, new_filename)
            log.info("new file path in {}".format(new_file_path))
            # 众多ffmpeg的库无法实现 -ss参数前置，所以直接使用命令行
            # +1s 确保不漏掉任何frame
            ffmpeg_cmd = ffmpeg_param % (start_time, duration + 1, origin_file_path, new_file_path)
            result = os.popen(ffmpeg_cmd)
            ret_msg = result.read()
            ret_suc = result.close()
            if ret_suc is not None:
                raise Exception(str(ret_suc) + ret_msg)
            log.info("file {} split result  {}".format(file_name, ret_msg))
            start_time += duration
            new_filename_ary.append(new_filename)
        self.db_con.insert_split_file_info_mpeg(file_name, "#".join(new_filename_ary),
                                           os.path.getsize(origin_file_path), datetime.datetime.now())
        return new_filename_ary

    def split_file_with_ffmpeg_fixed_size(self, file_name: str, max_size: int, duration: int, ffmpeg_param: str):
        file = self.db_con.get_split_file_info_by_source_name_mpeg(file_name)
        if file is not None:
            log.info("file {} already split.".format(file_name))
            return
        origin_file_path = os.path.join(self.source_dir, file_name)
        if not check_disk_space(self.dest_dir, os.path.getsize(origin_file_path)):
            log.info("disk free space is low. stop. current filename {}".format(file_name))
            exit(1)
        start_time = 0
        new_filename_ary = []
        media_duration = self.get_media_duration_time(origin_file_path)
        calc_duration = self.cacl_media_duration_by_fixed_size(max_size, origin_file_path)
        file_count_num = int(media_duration // duration) + 1
        if media_duration <= duration:
            log.info("media duration is {} , lt {}.".format(media_duration, duration))
            new_filename_ary.append(file_name)
        else:
            log.info("file split to {} .".format(file_count_num))
        for i in range(0, file_count_num):
            file_index = i + 1
            origin_filename = file_name
            t_of_a: list = origin_filename.split(".")
            t_of_a.insert(len(t_of_a) - 1, str(file_index))
            new_filename: str = ".".join(t_of_a)
            log.info("new file is {}. index {} for {}".format(new_filename, file_index, origin_filename))
            new_file_path = os.path.join(self.dest_dir, new_filename)
            log.info("new file path in {}".format(new_file_path))
            is_file_size_ok = True
            exec_time = 0
            real_duration = duration
            last_file_size = 0
            one_sec_size = 0
            while is_file_size_ok:
                # 众多ffmpeg的库无法实现 -ss参数前置，所以直接使用命令行
                if exec_time > 0:
                    log.info("reduce duration for file {} time {}".format(new_filename, exec_time))
                real_duration = calc_duration + exec_time
                if real_duration <= 0:
                    log.warning("file {} real_duration is {} exception.".format(new_filename, real_duration))
                    raise Exception("file {} real_duration is {} exception.".format(new_filename, real_duration))
                ffmpeg_cmd = ffmpeg_param % (start_time, real_duration, origin_file_path, new_file_path)
                result = os.popen(ffmpeg_cmd)
                ret_msg = result.read()
                ret_suc = result.close()
                if ret_suc is not None:
                    raise Exception(str(ret_suc) + ret_msg)
                cur_file_size = os.path.getsize(new_file_path)
                is_file_size_ok = not (cur_file_size + one_sec_size) >= max_size
                if not is_file_size_ok:
                    break
                if last_file_size != 0 and cur_file_size != last_file_size:
                    one_sec_size = cur_file_size - last_file_size
                    addtion_sec = int((max_size - cur_file_size) / one_sec_size)
                    if addtion_sec > (calc_duration / 2):
                        exec_time += calc_duration / 2
                    else:
                        exec_time += addtion_sec
                elif cur_file_size == last_file_size and is_file_size_ok:
                    if real_duration > media_duration:
                        # 计算时间比实际时间长，直接复制
                        new_filename_ary.append(new_filename)
                        self.db_con.insert_split_file_info_mpeg(file_name, "#".join(new_filename_ary),
                                                                os.path.getsize(origin_file_path),
                                                                datetime.datetime.now())
                        return new_filename_ary
                    elif start_time + real_duration > media_duration:
                        new_filename_ary.append(new_filename)
                        self.db_con.insert_split_file_info_mpeg(file_name, "#".join(new_filename_ary),
                                                                os.path.getsize(origin_file_path),
                                                                datetime.datetime.now())
                        # 计算时间分块时间已经到末尾，最大时长
                        return new_filename_ary
                    else:
                        exec_time += 1
                last_file_size = cur_file_size
            log.info("file {} split result  {}".format(file_name, ret_msg))
            start_time += real_duration
            new_filename_ary.append(new_filename)
        self.db_con.insert_split_file_info_mpeg(file_name, "#".join(new_filename_ary),
                                           os.path.getsize(origin_file_path), datetime.datetime.now())
        return new_filename_ary



    def split_dir_with_ffmpeg(self, exclude: list, duration: int, ffmpeg_param: str):
        l_files = os.listdir(self.source_dir)
        for f_name in l_files:
            need_continue = False
            for ec in exclude:
                re_ec = re.compile(ec)
                res_s = re_ec.search(f_name)
                if res_s is not None:
                    log.info("cause by {}, pass {}".format(ec, f_name))
                    need_continue = True
                    break
            split_file_info = self.db_con.get_split_file_info_by_source_name_mpeg(f_name)
            if split_file_info is not None:
                log.info("file {} already split.".format(f_name))
                need_continue = True
            if need_continue:
                continue
            self.split_file_with_ffmpeg(f_name, duration, ffmpeg_param)

    def split_dir_with_ffmpeg_fixed_size(self, exclude: list, max_size: int, ffmpeg_param: str):
        l_files = os.listdir(self.source_dir)
        for f_name in l_files:
            need_continue = False
            for ec in exclude:
                re_ec = re.compile(ec)
                res_s = re_ec.search(f_name)
                if res_s is not None:
                    log.info("cause by {}, pass {}".format(ec, f_name))
                    need_continue = True
                    break
            split_file_info = self.db_con.get_split_file_info_by_source_name_mpeg(f_name)
            if split_file_info is not None:
                log.info("file {} already split.".format(f_name))
                need_continue = True
            if need_continue:
                continue
            # 由于不同码率下同一时间长度产生的文件大小不一致，而要控制文件大小，则要控制时间，所以每个片段的时长要计算，而不能取固定值
            duration = self.cacl_media_duration_by_fixed_size(max_size, f_name)
            if duration is None or duration < 0:
                raise Exception("duration {} is wrong for file {}".format(duration, f_name))
            self.split_file_with_ffmpeg_fixed_size(f_name, max_size, duration, ffmpeg_param)

    def cacl_media_duration_by_fixed_size(self, max_size: int, file_name: str):
        probe: dict = ffmpeg.probe(os.path.join(self.source_dir, file_name))
        rate = 0
        for stream in probe.get("streams"):
            bit_rate_val = stream.get("bit_rate")
            if bit_rate_val is None:
                bit_rate_val = 64 * 1000
            bit_rate = int(bit_rate_val)
            if bit_rate is None:
                raise Exception("file {} stream {} bit_rate is None. probe is {}".format(file_name, stream.get("index"), probe))
            rate += bit_rate
        duration = 8 * (max_size - 10 * 1024 * 1024) // rate
        return duration

    def get_media_duration_time(self, file_path: str):
        try:
            result = os.popen("ffprobe -i \"%s\" -show_entries format=duration -v quiet -of csv=\"p=0\"" % file_path)
            result_plant = result.readlines().pop(0)
            result.close()
            return float(result_plant.strip())
        except Exception as e:
            log.error("ffprobe error file{}, exception{}".format(file_path, e))
            raise e

    def split_dir_with_translate(self, exclude: list, duration: int, ffmpeg_param: str):
        l_files = os.listdir(self.source_dir)
        for f_name in l_files:
            need_continue = False
            for ec in exclude:
                re_ec = re.compile(ec)
                res_s = re_ec.search(f_name)
                if res_s is not None:
                    log.info("cause by {}, pass {}".format(ec, f_name))
                    need_continue = True
                    break
            split_file_info = self.db_con.get_split_file_info_by_source_name_translate(f_name)
            if split_file_info is not None:
                log.info("file {} already split.".format(f_name))
                need_continue = True
            if need_continue:
                continue
            self.split_file_with_translate(f_name, duration, ffmpeg_param)

    # return split file name list
    def split_file_with_translate(self, file_name: str, duration: int, ffmpeg_param: str) -> list[str]:
        file = self.db_con.get_split_file_info_by_source_name_translate(file_name)
        if file is not None:
            log.info("file {} already split.".format(file_name))
            return []
        origin_file_path = os.path.join(self.source_dir, file_name)
        if not check_disk_space(self.dest_dir, os.path.getsize(origin_file_path)):
            log.info("disk free space is low. stop. current filename {}".format(file_name))
            exit(1)
        start_time = 0
        new_filename_ary = []
        media_duration = self.get_media_duration_time(origin_file_path)
        file_count_num = int(media_duration // duration) + 1
        if media_duration <= duration:
            log.info("media duration is {} , lt {}.".format(media_duration, duration))
            new_filename_ary.append(file_name)
        else:
            log.info("file split to {} .".format(file_count_num))
        for i in range(0, file_count_num):
            file_index = i + 1
            origin_filename = file_name
            t_of_a: list = origin_filename.split(".")
            t_of_a.insert(len(t_of_a) - 1, str(file_index))
            new_filename: str = ".".join(t_of_a)
            log.info("new file is {}. index {} for {}".format(new_filename, file_index, origin_filename))
            new_file_path = os.path.join(self.dest_dir, new_filename)
            log.info("new file path in {}".format(new_file_path))
            # 众多ffmpeg的库无法实现 -ss参数前置，所以直接使用命令行
            self.__ffmpeg_cmd__(ffmpeg_param, start_time, duration, origin_file_path, new_file_path)
            # ffmpeg_cmd = ffmpeg_param % (start_time, duration, "\"" + origin_file_path + "\"", "\"" + new_file_path + "\"")
            # log.info("cmd: {}".format(ffmpeg_cmd))
            # result = os.popen(ffmpeg_cmd)
            # ret_msg = result.read()
            # ret_suc = result.close()
            # if ret_suc is not None:
            #     raise Exception(ret_suc + ret_msg)
            # log.info("file {} split result  {}".format(file_name, ret_msg))
            # result.close()
            start_time += duration
            new_filename_ary.append(new_filename)
        self.db_con.insert_split_file_info_translate(file_name, "#".join(new_filename_ary),
                                                os.path.getsize(origin_file_path), datetime.datetime.now())
        return new_filename_ary

    def __ffmpeg_cmd__(self, ffmpeg_param: str, start_time: int, duration: int, origin_file_path: str, new_file_path: str):
        ffmpeg_cmd = ffmpeg_param % (start_time, duration, "\"" + origin_file_path + "\"", "\"" + new_file_path + "\"")
        log.info("cmd: {}".format(ffmpeg_cmd))
        result = os.popen(ffmpeg_cmd)
        ret_msg = result.read()
        ret_suc = result.close()
        if ret_suc is not None:
            log.error("ffmpeg_cmd: {}".format(ffmpeg_cmd))
            raise Exception(str(ret_suc) + ret_msg)
        log.info("file {} split result  {}".format(origin_file_path, ret_msg))
        result.close()

class Combo:
    db_con: DbCon = None
    source_dir: str = None
    dest_dir: str = None

    def __init__(self, db_con, source_dir: str,  dest_dir: str):
        self.db_con = db_con
        self.dest_dir = dest_dir
        self.source_dir = source_dir

    def combo_file(self, file_name: str):
        source_name = self.__get_source_name_by_new_name(file_name)
        if os.path.exists(os.path.join(self.dest_dir, source_name)):
            log.info("source {} already found.".format(source_name))
            return
        log.info("parse {} to source_name is {}".format(file_name, source_name))
        file_info = self.db_con.get_split_file_info_by_source_name(source_name)
        if file_info is None:
            log.info("source file info {} not found.".format(source_name))
            return
        source_file_path = os.path.join(self.dest_dir, source_name)
        with open(source_file_path, "wb") as f:
            new_name: str = file_info[2]
            new_name_ary = new_name.split("#")
            for nn in new_name_ary:
                split_file_path = os.path.join(self.source_dir, nn)
                if not os.path.exists(split_file_path):
                    log.info("split file {} not found. exit this process.".format(split_file_path))
                    return
                with open(split_file_path, "rb") as sf:
                    buff_size = 1024 * 1024 * 10
                    mb = sf.read(buff_size)
                    while mb:
                        f.write(mb)
                        mb = sf.read(buff_size)
                log.info("split file {} combo done.".format(nn))

    def combo_dir(self):
        l_files = os.listdir(self.source_dir)
        for f_name in l_files:
            self.combo_file(f_name)

    def __get_source_name_by_new_name(self, new_name) -> str:
        new_name_ary = new_name.split(".")
        new_name_ary.pop(-2)
        return ".".join(new_name_ary)

    # ffmpeg -f concat -safe 0 -i f.txt -c copy -strict -2 concated.mp4
    # 由于直接copy流，ffmpeg在前面拆分视频时，会在关键帧的位置重复。所以这里合并视频的时候，会在片头片尾重复一小段视频
    def combo_file_with_ffmpeg(self, file_name: str, ffmpeg_param: str):
        source_name = self.__get_source_name_by_new_name(file_name)
        if os.path.exists(os.path.join(self.dest_dir, source_name)):
            log.info("source {} already found.".format(source_name))
            return
        log.info("parse {} to source_name is {}".format(file_name, source_name))
        file_info = self.db_con.get_split_file_info_by_source_name_mpeg(source_name)
        if file_info is None:
            log.info("source file info {} not found.".format(source_name))
            return
        source_file_path = os.path.join(self.dest_dir, source_name)
        new_name: str = file_info[2]
        new_name_ary = new_name.split("#")
        new_name_path_ary: list = []
        for nn in new_name_ary:
            split_file_path = os.path.join(self.source_dir, nn)
            if not os.path.exists(split_file_path):
                log.info("split file {} not found. exit this process.".format(split_file_path))
                return
            new_name_path_ary.append("file '" + split_file_path.replace("\\", "/") + "'")
        concat_file_path = os.path.join(self.dest_dir, "concat.txt")
        with open(concat_file_path, "w", encoding="u8") as cf:
            cf.write('\n'.join(new_name_path_ary))
        cmd = ffmpeg_param % (concat_file_path, "\"" + source_file_path + "\"")
        result = os.popen(cmd)
        log.info("split file {} reuslut is {} combo done.".format(source_name, result.readlines()))
        result.close()

    def combo_dir_with_ffmpeg(self, ffmpeg_param: str):
        l_files = os.listdir(self.source_dir)
        for f_name in l_files:
            self.combo_file_with_ffmpeg(f_name, ffmpeg_param)


class SplitAndEncrypt:
    combo: Combo
    split: Spliter
    encrypt: MediaEncrypt
    dbcon: DbCon
    encrypt_key: str
    source_dir: str
    dest_dir: str
    max_size: int

    def __init__(self, db_con: DbCon, source_dir: str,  dest_dir: str, key: str, max_size: int = 99 * 1024 * 1024):
        self.db_con = db_con
        self.combo = Combo(db_con, source_dir, dest_dir)
        self.split = Spliter(db_con, source_dir, dest_dir, max_size)
        self.encrypt = MediaEncrypt(db_con)
        self.encrypt_key = key
        self.source_dir = source_dir
        self.dest_dir = dest_dir
        self.max_size = max_size

    def split_and_encrypt_file(self, file_name: str) -> str:
        tmp_dir: str = os.path.join(self.source_dir, "tmp")
        if not os.path.exists(tmp_dir):
            os.mkdir(tmp_dir)
        s: Spliter = Spliter(self.db_con, self.source_dir, tmp_dir, self.max_size)
        split_file_name_list: list[str] = s.split_file(file_name)
        group_name: str = self.db_con.get_split_file_info_by_source_name(file_name)[0]
        log.info("split file list is {} group name is {}".format(split_file_name_list, group_name))
        self.encrypt.encrypt_files_with_subfix_by_group(self.encrypt_key, tmp_dir, self.dest_dir, group_name)
        log.info("encrypt {} done, delete source files".format(split_file_name_list))
        self.delete_files(tmp_dir, split_file_name_list)
        return tmp_dir

    def split_and_encrypt_dir(self, exclude: list):
        l_files = os.listdir(self.source_dir)
        for f_name in l_files:
            need_continue = False
            for ec in exclude:
                re_ec = re.compile(ec)
                res_s = re_ec.search(f_name)
                if res_s is not None:
                    log.info("cause by {}, pass {}".format(ec, f_name))
                    need_continue = True
                    break
            split_file_info = self.db_con.get_split_file_info_by_source_name(f_name)
            if split_file_info is not None:
                log.info("file {} already split.".format(f_name))
                need_continue = True
            if need_continue:
                continue
            if not os.path.isfile(os.path.join(self.source_dir, f_name)):
                log.info("file {} not file.".format(f_name))
                continue
            self.split_and_encrypt_file(f_name)

    def decrypt_and_combo_file(self, file_name_array: list):
        tmp_dir: str = os.path.join(self.source_dir, "tmp")
        delete_file_name_array: list = []
        if not os.path.exists(tmp_dir):
            os.mkdir(tmp_dir)
        for fn in file_name_array:
            fn_path: str = os.path.join(self.source_dir, fn[2])
            dest_path = os.path.join(tmp_dir, fn[1])
            self.encrypt.decrypt_file(self.encrypt_key, fn_path, dest_path)
            delete_file_name_array.append(fn[1])
        log.info("decrypt {} done".format(file_name_array))
        cb: Combo = Combo(self.db_con, tmp_dir, self.dest_dir)
        cb.combo_dir()
        log.info("combo {} done".format(file_name_array))
        self.delete_files(tmp_dir, delete_file_name_array)

    def decrypt_and_combo_dir(self, exclude: list):
        l_files: list[str] = os.listdir(self.source_dir)
        already_process_file_arr: list[str] = []
        for f_name in l_files:
            need_continue = False
            for ec in exclude:
                re_ec = re.compile(ec)
                res_s = re_ec.search(f_name)
                if res_s is not None:
                    log.info("cause by {}, pass {}".format(ec, f_name))
                    need_continue = True
                    break
            if need_continue:
                continue
            if not os.path.isfile(os.path.join(self.source_dir, f_name)):
                log.info("file {} not file.".format(f_name))
                continue
            # 判读是否为group文件
            if f_name.find("#") == -1:
                log.warning("file {} not a group encrypt file.".format(f_name))
                continue
            else:
                # 是否是已处理过的组文件
                if f_name in already_process_file_arr:
                    log.warning("file {} already handled".format(f_name))
                    continue
                # 匹配本地文件和数据库记录
                f_group_name: str = f_name.split("#")[0]
                file_group_array: list[str] = []
                for f in l_files:
                    if f.find(f_group_name + "#") != -1:
                        file_group_array.append(f)
                new_filename_array = self.encrypt.get_all_real_filename_by_group(f_group_name)
                if len(new_filename_array) != len(file_group_array):
                    log.warning("local file not match db record. local files {}, db records {}"
                                .format(file_group_array, new_filename_array))
                log.info("start decrypting and combo file {}".format(new_filename_array))
                self.decrypt_and_combo_file(new_filename_array)
                for nf in new_filename_array:
                    already_process_file_arr.append(nf[2])
                log.info("file {}  decrypted and combed".format(new_filename_array))

    # return translate files dir
    def split_translate_and_encrypt_file(self, file_name: str, duration: int, ffmpeg_param: str) -> str:
        tmp_dir: str = os.path.join(self.source_dir, "tmp")
        if not os.path.exists(tmp_dir):
            os.mkdir(tmp_dir)
        s: Spliter = Spliter(self.db_con, self.source_dir, tmp_dir, 0)
        split_file_name_list: list[str] = s.split_file_with_translate(file_name, duration, ffmpeg_param)
        log.info("split file list is {}".format(split_file_name_list))
        self.encrypt.encrypt_files_with_subfix(self.encrypt_key, tmp_dir, self.dest_dir)
        log.info("encrypt {} done, delete source files".format(split_file_name_list))
        self.delete_files(tmp_dir, split_file_name_list)
        return tmp_dir

    # return ffmpeg files dir
    def split_ffmpeg_and_encrypt_file(self, file_name: str, duration: int, ffmpeg_param: str) -> str:
        tmp_dir: str = os.path.join(self.source_dir, "tmp")
        shutil.rmtree(tmp_dir)
        if not os.path.exists(tmp_dir):
            os.mkdir(tmp_dir)
        s: Spliter = Spliter(self.db_con, self.source_dir, tmp_dir, 0)
        split_file_name_list: list[str] = s.split_file_with_ffmpeg(file_name, duration, ffmpeg_param)
        log.info("split file list is {}".format(split_file_name_list))
        self.encrypt.encrypt_files_with_subfix(self.encrypt_key, tmp_dir, self.dest_dir)
        log.info("encrypt {} done, delete source files".format(split_file_name_list))
        self.delete_files(tmp_dir, split_file_name_list)
        return tmp_dir

    def split_ffmpeg_and_encrypt_file_fixed_size(self, file_name: str, duration: int, max_size: int, ffmpeg_param: str) -> str:
        tmp_dir: str = os.path.join(self.source_dir, "tmp")
        shutil.rmtree(tmp_dir)
        if not os.path.exists(tmp_dir):
            os.mkdir(tmp_dir)
        s: Spliter = Spliter(self.db_con, self.source_dir, tmp_dir, 0)
        split_file_name_list: list[str] = s.split_file_with_ffmpeg_fixed_size(file_name, max_size, duration, ffmpeg_param)
        log.info("split file list is {}".format(split_file_name_list))
        self.encrypt.encrypt_files_with_subfix(self.encrypt_key, tmp_dir, self.dest_dir)
        log.info("encrypt {} done, delete source files".format(split_file_name_list))
        self.delete_files(tmp_dir, split_file_name_list)
        return tmp_dir

    def delete_files(self, dir_path: str, file_name_list: list[str]):
        for fn in file_name_list:
            fn_path: str = os.path.join(dir_path, fn)
            if os.path.exists(fn_path):
                os.remove(fn_path)
                log.info("file {} deleted".format(fn_path))
            else:
                log.warning("file {} not found.".format(fn_path))

    def split_translate_and_encrypt_dir(self, exclude: list, duration: int, ffmpeg_param: str):
        l_files = os.listdir(self.source_dir)
        for f_name in l_files:
            need_continue = False
            for ec in exclude:
                re_ec = re.compile(ec)
                res_s = re_ec.search(f_name)
                if res_s is not None:
                    log.info("cause by {}, pass {}".format(ec, f_name))
                    need_continue = True
                    break
            split_file_info = self.db_con.get_split_file_info_by_source_name_translate(f_name)
            if split_file_info is not None:
                log.info("file {} already split.".format(f_name))
                need_continue = True
            if need_continue:
                continue
            if not os.path.isfile(os.path.join(self.source_dir, f_name)):
                log.info("file {} not file.".format(f_name))
                continue
            self.split_translate_and_encrypt_file(f_name, duration, ffmpeg_param)

    # 不保证最终文件大小
    def split_ffmpeg_and_encrypt_dir(self, exclude: list, max_size: int, ffmpeg_param: str):
        l_files = os.listdir(self.source_dir)
        for f_name in l_files:
            need_continue = False
            for ec in exclude:
                re_ec = re.compile(ec)
                res_s = re_ec.search(f_name)
                if res_s is not None:
                    log.info("cause by {}, pass {}".format(ec, f_name))
                    need_continue = True
                    break
            split_file_info = self.db_con.get_split_file_info_by_source_name_mpeg(f_name)
            if split_file_info is not None:
                log.info("file {} already split.".format(f_name))
                need_continue = True
            if need_continue:
                continue
            if not os.path.isfile(os.path.join(self.source_dir, f_name)):
                log.info("file {} not file.".format(f_name))
                continue
            #由于不同码率下同一时间长度产生的文件大小不一致，而要控制文件大小，则要控制时间，所以每个片段的时长要计算，而不能取固定值
            duration = self.cacl_media_duration_by_fixed_size(max_size, f_name)
            if duration is None or duration < 0:
                raise Exception("duration {} is wrong for file {}".format(duration, f_name))
            self.split_ffmpeg_and_encrypt_file(f_name, duration, ffmpeg_param)

    # 保证最终文件大小一定小于max_size
    def split_ffmpeg_and_encrypt_dir_fixed_size(self, exclude: list, max_size: int, ffmpeg_param: str):
        l_files = os.listdir(self.source_dir)
        for f_name in l_files:
            if f_name.endswith("part"):
                log.info("file {} is not video.".format(f_name))
                continue
            new_f_name = handle_file_name(f_name)
            if new_f_name is not None:
                log.info("rename file {} to {}".format(f_name, new_f_name))
                os.rename(os.path.join(self.source_dir, f_name), os.path.join(self.source_dir, new_f_name))
                f_name = new_f_name
            need_continue = False
            for ec in exclude:
                re_ec = re.compile(ec)
                res_s = re_ec.search(f_name)
                if res_s is not None:
                    log.info("cause by {}, pass {}".format(ec, f_name))
                    need_continue = True
                    break
            split_file_info = self.db_con.get_split_file_info_by_source_name_mpeg(f_name)
            if split_file_info is not None:
                log.info("file {} already split.".format(f_name))
                need_continue = True
            if need_continue:
                continue
            if not os.path.isfile(os.path.join(self.source_dir, f_name)):
                log.info("file {} not file.".format(f_name))
                continue
            # 由于不同码率下同一时间长度产生的文件大小不一致，而要控制文件大小，则要控制时间，所以每个片段的时长要计算，而不能取固定值
            duration = self.cacl_media_duration_by_fixed_size(max_size, f_name)
            if duration is None or duration < 0:
                raise Exception("duration {} is wrong for file {}".format(duration, f_name))
            self.split_ffmpeg_and_encrypt_file_fixed_size(f_name, duration, max_size, ffmpeg_param)
            #self.generate_thumbnail(os.path.join(self.source_dir, f_name), os.path., 60, 300)

    def cacl_media_duration_by_fixed_size(self, max_size: int, file_name: str):
        probe: dict = ffmpeg.probe(os.path.join(self.source_dir, file_name))
        rate = 0
        for stream in probe.get("streams"):
            bit_rate_val = stream.get("bit_rate")
            if bit_rate_val is None:
                bit_rate_val = 64 * 1000
            bit_rate = int(bit_rate_val)
            if bit_rate is None:
                raise Exception("file {} stream {} bit_rate is None. probe is {}".format(file_name, stream.get("index"), probe))
            rate += bit_rate
        duration = 8 * (max_size - 10 * 1024 * 1024) // rate
        return duration

class YiKeClient:
    client: YiKeAPI
    thumb_dir_path: str

    def __init__(self, cookies: str = None, thumb_dir_path: str = os.path.join(os.getcwd(), "thumb")):
        self.thumb_dir_path = thumb_dir_path
        if not os.path.exists(self.thumb_dir_path):
            os.mkdir(self.thumb_dir_path)
        if cookies is not None:
            self.client = YiKeAPI(YiKeClient.__cookie_to_dic__(self, cookies))
        else:
            self.client = YiKeAPI(browser_cookie3.firefox())

    def upload_file(self, file_path: str, album_name=None):
        item_info = self.client.upload_1file(file_path)
        if album_name is not None:
            all_albums = self.client.getAlbumList_All("Album")
            al_info = None
            for al in all_albums:
                if al.info['title'] == album_name:
                    al_info = al
                    break
            al_info.append(item_info)
        log.info("file {} upload done".format(file_path))

    def list_page(self, type_name: str = "Item", cursor=None):
        return self.client.get_self_1page(type_name, cursor)

    def upload_dirs(self, dir: str, exclude: list = None, album_name=None, method_progress_bar_update=None):
        l_files: list[str] = os.listdir(dir)
        for f_name in l_files:
            need_continue = False
            for ec in exclude:
                re_ec = re.compile(ec)
                res_s = re_ec.search(f_name)
                if res_s is not None:
                    log.info("cause by {}, pass {}".format(ec, f_name))
                    need_continue = True
                    break
            if need_continue:
                continue
        log.info("start upload dir {} to yiKeAlbum".format(dir))
        index = 0
        for fn in l_files:
            self.upload_file(os.path.join(dir, fn), album_name)
            if method_progress_bar_update is not None:
                index += 1
                method_progress_bar_update(index / len(l_files))

    def upload_dirs_qt(self, dir: str, exclude: list = None, album_name=None, method_progress_bar_update=None):
        self.upload_dirs(dir, exclude, album_name, method_progress_bar_update)

    def download(self, item, dest_dir: str):
        item.download(dest_dir)

    def __cookie_to_dic__(self, cookie) -> dict:
        cookie_dic = {}
        for i in cookie.split('; '):
            cookie_dic[i.split('=')[0]] = "=".join(i.split('=')[1:])
        return cookie_dic

    def play(self, file_path: str):
        os.popen("ffplay {}".format(file_path))

    def __do_generate_thumbnail(self, in_filename, out_filename, time, width):
        try:
            (
                ffmpeg
                .input(in_filename, ss=time)
                .filter('scale', width, -1)
                .output(out_filename, vframes=1)
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
        except ffmpeg.Error as e:
            log.warning(e.stderr.decode())
            return

    def generate_thumbnail(self, file_path: str, sep: str, thumb_dir_path: str = os.path.join(os.getcwd(), "thumb"),
                           time: int = 60):
        file_name = os.path.split(file_path)[-1]
        thumb_path = None
        if thumb_dir_path is None:
            thumb_path = self.thumb_dir_path
        else:
            thumb_path = thumb_dir_path
        thumb_file_path = os.path.join(thumb_path, file_name) + ".jpg"
        self.__do_generate_thumbnail(file_path, thumb_file_path, time, 300)
        return thumb_file_path

def check_disk_space(path: str, need_size: int):
    usage = psutil.disk_usage(path.split(os.sep)[0])
    log.info("path {} disk usage {}".format(path, usage))
    return usage.free > need_size


def handle_file_name(s):
    rep_str = repeated(s)
    new_s = s
    while rep_str is not None and len(rep_str) > 3:
        new_s = new_s.replace(rep_str, "", new_s.count(rep_str) - 1)
        rep_str = repeated(new_s)
    new_s = new_s.strip()
    new_s = new_s.replace("黄色仓库-hsck.net", "")
    new_s = new_s.replace("迅雷", "")
    new_s = new_s.replace("下载", "")
    new_s = new_s.replace("详情介绍", "")
    new_s = new_s.replace("在线观看", "")
    new_s = new_s.replace("-", "")
    new_s = new_s.strip()
    return new_s
def repeated(s):
    max_len_rep_str = ""
    for start_index in range(0, int(len(s) / 2)):
        for end_index in range(1, int(len(s) / 2)):
            t = s[start_index: end_index]
            if s.count(t) >= 2:
                max_len_rep_str = t
            else:
                return max_len_rep_str
    return None




# <del>storage use SF or ST (codec and no repeat frame), r18 use STAE</del>
# for performance use CFAE
if __name__ == '__main__':
    key = sys.argv[1]
    source_dir = sys.argv[2]
    dest_dir = sys.argv[3]
    type = sys.argv[4]  # [E|D|S|C] E encrypt D decrypt S split(can't preview) C combo SF (split with ffmpeg)
    # CF (combo with ffmpeg) ST (translate codec with ffmpeg) CT (combo with ffmpeg equals CF)
    # SAE(split and encrypt) CAE(decrypt and combo)
    # SFAE (split with ffmpeg and encrypt)
    # CFAE (combo with ffmpeg and dencrypt)
    # STAE (split translate with ffmpeg and encrypt)
    # CTAE (decrypt and combo translate files with ffmpeg)
    # !!! CF and SF timeline is not accurate
    # YKU (upload to yiKeAlbum)
    log.info("start date in {} source_dir={}, dest_dir={}".format(datetime.datetime.now(), source_dir, dest_dir))
    dbcon = DbCon()
    try:
        if type == "E":
            encrypt = MediaEncrypt(dbcon)
            encrypt.encrypt_files(key, source_dir, dest_dir)
        elif type == "D":
            encrypt = MediaEncrypt(dbcon)
            encrypt.decrypt_files(key, source_dir, dest_dir)
        elif type == "S":
            split = Spliter(dbcon, source_dir, dest_dir, 99 * 1024 * 1024)
            split.split_dir([r'*.ini'])
        elif type == "C":
            combo = Combo(dbcon, source_dir, dest_dir)
            combo.combo_dir()
        elif type == "SF":
            sf = Spliter(dbcon, source_dir, dest_dir, 0)
            ffmpeg_param = "ffmpeg -ss %d -t %d -accurate_seek -i \"%s\" -codec copy -avoid_negative_ts 1 \"%s\" -loglevel warning -y"
            sf.split_dir_with_ffmpeg([r'*.ini'], int(60 * 1.1), ffmpeg_param)
        elif type == "CF" or type == "CT":
            combo = Combo(dbcon, source_dir, dest_dir)
            ffmpeg_param = "ffmpeg -f concat -safe 0 -i %s -c copy -strict -2 %s -loglevel warning"
            combo.combo_dir_with_ffmpeg(ffmpeg_param)
        elif type == "ST":
            st = Spliter(dbcon, source_dir, dest_dir, 0)
            ffmpeg_param = "ffmpeg -ss %d -t %d -i \"%s\" -c:v h264_qsv -global_quality 10 -c:a mp3 -strict experimental \"%s\" -loglevel warning -y"
            st.split_dir_with_translate([r'*.ini'], int(60 * 1.0), ffmpeg_param)
        elif type == "SAE":
            se = SplitAndEncrypt(dbcon, source_dir, dest_dir, key, 99 * 1024 * 1024)
            se.split_and_encrypt_dir([r'*.ini'])
        elif type == "CAE":
            se = SplitAndEncrypt(dbcon, source_dir, dest_dir, key, 99 * 1024 * 1024)
            se.decrypt_and_combo_dir([r'*.ini'])
        elif type == "SFAE":
            # 转码对于电脑负担还是很大的。所以尽量采用本方式
            ffmpeg_param = "ffmpeg -ss %d -t %d -accurate_seek -i \"%s\" -codec copy -avoid_negative_ts 1 \"%s\" -loglevel warning -y"
            sfae = SplitAndEncrypt(dbcon, source_dir, dest_dir, key)
            sfae.split_ffmpeg_and_encrypt_dir([r'*.ini'], 99 * 1024 * 1024, ffmpeg_param)
        elif type == "CFAE":
            """
import os
import tempfile
import ffmpy

# 创建临时文件
temp_dir = tempfile.mktemp()
os.mkdir(temp_dir)
concat_file = os.path.join(temp_dir, 'concat_list.txt')

with open(concat_file, 'w', encoding='utf-8') as f:
    f.write('\n'.join([
        'file C:/1.mp4',
        'file C:/2.mp4',
        'file C:/3.mp4',
    ]))

ff = ffmpy.FFmpeg(
    global_options=['-f', 'concat'],
    inputs={concat_file: None},
    outputs={'output.mp4': ['-c', 'copy']}
)

ff.run()
            """

            raise NotImplementedError()
        elif type == "STAE":
            print("in cpu platform use:ffmpeg -ss %d -t %d -i %s -c:v libx264 -crf 20 -maxrate 6000k -bufsize 5000k  -c:a copy -strict experimental %s -loglevel warning -y")
            print("in amd platform use:")
            stae = SplitAndEncrypt(dbcon, source_dir, dest_dir, key)
            ffmpeg_param = "ffmpeg -ss %d -t %d -i \"%s\" -c:v h264_qsv -global_quality 15 -c:a mp3 -strict experimental \"%s\" -loglevel warning -y"
            stae.split_translate_and_encrypt_dir([r'*.ini'], int(60 * 1.0), ffmpeg_param)
        elif type == "CTAE":
            raise NotImplementedError()
        elif type == "YKU": #TODO test
            album_name = sys.argv[5]
            cookies = sys.argv[6]
            ykClient = YiKeClient(cookies)
            if album_name == "x":
                album_name = None
            ykClient.upload_dirs(source_dir, [r'*.ini'], album_name)
        else:
            raise NotImplementedError()
    except Exception as e:
        log.info(e.with_traceback())
        if dbcon is not None:
            dbcon.con.close()
    log.info("done date in {}".format(datetime.datetime.now()))

