#!/usr/bin/python3

import logging
import os
import sys
import shutil
import datetime

logging.basicConfig(filename="tools.log", level=logging.INFO)
log = logging.getLogger("tools")


class FileTools:

    output_dir = None
    log = logging.getLogger("file_tools")

    def __init__(self, output_dir):
        self.output_dir = output_dir

    def move_subdir_file(self, dest_dir, prefix_name):
        files = os.listdir(dest_dir)
        for file in files:
            file_path = os.path.join(dest_dir, file)
            if os.path.isdir(file_path):
                self.log.info("enter subdir {}".format(file_path))
                self.move_subdir_file(file_path, prefix_name)
            if not os.path.isfile(file_path):
                self.log.info("{} is not file. skip it.".format(file_path))
                continue
            if os.path.isdir(dest_dir):
                dir_name = dest_dir.split(os.sep)[-1]
            else:
                self.log.warning("dest_dir {} is not dir.".format(dest_dir))
                sys.exit(-1)
            if prefix_name is not None:
                new_file_name = prefix_name + "-" + file
            elif dir_name not in file:
                new_file_name = dir_name + "-" + file
                log.info("file {} rename filename to {}".format(file, new_file_name))
            else:
                new_file_name = file
            new_file_path = os.path.join(self.output_dir, new_file_name)
            shutil.move(file_path, new_file_path)
            self.log.info("move file {} to {} done.".format(file_path, new_file_path))


if __name__ == '__main__':
    type = sys.argv[1]  # [M] M MoveFile

    try:
        if type == "M":
            output_dir = sys.argv[2]
            source_dir = sys.argv[3]
            prefix_name = sys.argv[4]
            log.info(
                "start date in {} output_dir={}, source_dir={}, prefix_name={}".format(datetime.datetime.now(),
                                                                                       output_dir, source_dir, prefix_name))
            file_tools = FileTools(output_dir)
            if prefix_name == "None":
                prefix_name = None
            file_tools.move_subdir_file(source_dir, prefix_name)
        else:
            log.warning("type {} not supported".format(type))
    except Exception as e:
        log.info(e)
    log.info("done date in {}".format(datetime.datetime.now()))