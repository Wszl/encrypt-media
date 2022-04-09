#!/usr/bin/python3

import logging
import os
import re
import sqlite3
import uuid
import datetime
import sys
import psutil

logging.basicConfig(filename="main.log", level=logging.INFO)
log = logging.getLogger("main")

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

    def insert_split_file_info(self, source_name, new_name, file_size, date):
        cursor = self.con.cursor()
        cursor.execute("insert into split_file_info (source_name, new_name, `size`, `date`) values (?, ?, ?, ?)", (source_name, new_name, file_size, date))
        cursor.close()
        self.con.commit()

    def get_split_file_info_by_source_name(self, source_name) -> list:
        cursor = self.con.cursor()
        cursor.execute("select * from split_file_info where source_name=?", (source_name, ))
        return cursor.fetchone()

    def get_db_con(self):
        if self.con is not None:
            return self.con
        self.con = sqlite3.connect(self.db_path)
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


class MediaEncrypt:

    con = None

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

    def encrypt_file(self, key, file, output_file, chunk_size=1024 * 1024 * 10):
        with open(file, "rb") as f, open(output_file, "wb") as of:
            chuck_block = f.read(chunk_size)
            while chuck_block:
                out_chuck = self.encrypt_xor(chuck_block, bytes(key, "u8"))
                of.write(out_chuck)
                chuck_block = f.read(chunk_size)

    def decrypt_file(self, key, file, output_file, chunk_size=1024 * 1024 * 10):
        self.encrypt_file(key, file, output_file, chunk_size)

    def anonymous_filename(self, source_name, file_size):
        new_name = str(uuid.uuid1())
        self.con.insert_meta(source_name, new_name, file_size, datetime.datetime.now())
        return new_name

    def get_real_filename(self, anonymous_name):
        meta_row = self.con.get_meta_by_new_name(anonymous_name)
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
            log.info("start decrypting file {}".format(file))
            self.decrypt_file(key, file_path, os.path.join(dest_dir_path, new_filename))
            log.info("file {} decrypted.".format(file))

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

    def split_file(self, file_name: str):
        file = self.db_con.get_split_file_info_by_source_name(file_name)
        if file is not None:
            log.info("file {} already split.".format(file_name))
            return
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

def check_disk_space(path: str, need_size: int):
    usage = psutil.disk_usage(path.split(os.sep)[0])
    log.info("path {} disk usage {}".format(path, usage))
    return usage.free > need_size


if __name__ == '__main__':
    key = sys.argv[1]
    source_dir = sys.argv[2]
    dest_dir = sys.argv[3]
    type = sys.argv[4]  # [E|D|S|C] E encrypt D decrypt S split C combo
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
            split.split_dir([r'.*ini'])
        elif type == "C":
            combo = Combo(dbcon, source_dir, dest_dir)
            combo.combo_dir()
        else:
            raise NotImplementedError()
    except Exception as e:
        log.info(e)
        if dbcon is not None:
            dbcon.con.close()
    log.info("done date in {}".format(datetime.datetime.now()))

