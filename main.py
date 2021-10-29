#!/usr/bin/python3

import logging
import os
import sqlite3
import uuid
import datetime
import sys
import struct

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

class DbCon:

    con = None

    def __init__(self):
        self.get_db_con()

    def __del__(self):
        self.con.close()

    def init_meta_db(self):
        cursor = self.con.cursor()
        cursor.execute(table_ddl_meta)
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

    def get_db_con(self):
        if self.con is not None:
            return self.con
        self.con = sqlite3.connect("meta.db")
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


if __name__ == '__main__':
    key = sys.argv[1]
    source_dir = sys.argv[2]
    dest_dir = sys.argv[3]
    type = sys.argv[4]  # [E|D] E encrypt D decrypt
    log.info("start date in {} source_dir={}, dest_dir={}".format(datetime.datetime.now(), source_dir, dest_dir))
    dbcon = DbCon()
    encrypt = MediaEncrypt(dbcon)
    try:
        if type == "E":
            encrypt.encrypt_files(key, source_dir, dest_dir)
        else:
            encrypt.decrypt_files(key, source_dir, dest_dir)
    except Exception as e:
        log.info(e)
        dbcon.con.close()
    log.info("done date in {}".format(datetime.datetime.now()))

