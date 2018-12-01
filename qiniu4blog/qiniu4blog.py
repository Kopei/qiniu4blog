#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os, time, sys, ConfigParser, platform, urllib, pyperclip, signal, threading
from mimetypes import MimeTypes
from os.path import expanduser

import boto3 as boto3
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler


# 使用watchdog 监控文件夹中的图像
class MyHandler(PatternMatchingEventHandler):
    patterns = ["*.jpeg", "*.jpg", "*.png", "*.bmp", "*.gif","*.tiff"]
    ignore_directories = True
    case_sensitive = False
    def process(self, event):
        if event.event_type == 'created'or event.event_type == 'modified': #如果是新增文件或修改的文件
            myThread(event.src_path).start() # 开启线程
    def on_modified(self, event):
        self.process(event)
    def on_created(self, event):
        self.process(event)


# 使用多线程上传
class myThread(threading.Thread):
    def __init__(self, filePath): #filePath 文件路径 和 上传模式
        threading.Thread.__init__(self)
        self.filePath = filePath
    def run(self):
        threadLock.acquire()
        job(self.filePath)
        threadLock.release()


# 上传图像、复制到粘贴板、写到文件
def job(file):
    url = upload_with_file_path(file, bucket)
    pyperclip.copy(url)
    pyperclip.paste()
    print url
    homedir = expanduser("~")  # 获取用户主目录
    with open(homedir+'/MARKDOWN_FORMAT_URLS.txt', 'a') as f:
        image = '![' + url + ']' + '(' + url + ')' + '\n'
        f.write(image + '\n')

#-----------------配置--------------------
homedir = expanduser("~")  # 获取用户主目录
config = ConfigParser.RawConfigParser()
config.read(homedir+'/s3-kopei.cfg')  # 读取配置文件
mime = MimeTypes()
threadLock = threading.Lock()


# 优雅退出
def exit_gracefully(signum, frame):
    signal.signal(signal.SIGINT, original_sigint)
    try:
        if raw_input("\nReally quit? (y/n)> ").lower().startswith('y'):
            sys.exit(1)
    except KeyboardInterrupt:
        print("Ok ok, quitting")
        sys.exit(1)
    signal.signal(signal.SIGINT, exit_gracefully)

original_sigint = signal.getsignal(signal.SIGINT)
signal.signal(signal.SIGINT, exit_gracefully)

try:
    bucket = config.get('config', 'bucket')  # 设置  bucket
    accessKey = config.get('config', 'accessKey')  # 设置  accessKey
    secretKey = config.get('config', 'secretKey')  # 设置  secretKey
    path_to_watch = config.get('config', 'path_to_watch')  # 设置   监控文件夹
    enable = config.get('custom_url', 'enable')  # 设置自定义使能 custom_url
    addr = config.get('custom_url', 'addr')
except ConfigParser.NoSectionError, err:
    print 'Error Config File:', err


# 设置编码
def setCodeingByOS():
    if 'cygwin' in platform.system().lower():
        return 'GBK'
    elif os.name == 'nt' or platform.system() == 'Windows':
        return 'GBK'
    elif os.name == 'mac' or platform.system() == 'Darwin':
        return 'utf-8'
    elif os.name == 'posix' or platform.system() == 'Linux':
        return 'utf-8'


# 处理七牛返回结果
def parseRet(retData, respInfo):
    if retData != None:
        for k, v in retData.items():
            if k[:2] == "x:":
                print(k + ":" + v)
        for k, v in retData.items():
            if k[:2] == "x:" or k == "hash" or k == "key":
                continue
            else:
                print(k + ":" + str(v))
    else:
        print("Upload file failed!")

# 上传文件方式 1
def upload_with_file_path(filePath, bucket):
    fileName = "".join(filePath.rsplit(path_to_watch))[1:]
    s3 = boto3.resource('s3')
    obj = s3.Object(bucket, fileName)
    obj.upload_file(filePath)
    object_acl = s3.ObjectAcl(bucket, fileName)
    response = object_acl.put(ACL='public-read')
    print response
    return addr + urllib.quote(fileName.decode(setCodeingByOS()).encode('utf-8'))

#-----------------window platform---------------start
# window下的监控文件夹变动方式-获取所有文件路径
def get_filepaths(directory):
    file_paths = []  # List which will store all of the full filepaths.
    for root, directories, files in os.walk(directory):
        for filename in files:
            # Join the two strings in order to form the full filepath.
            filepath = os.path.join(root, filename)
            file_paths.append(filepath)  # Add it to the list.
    return file_paths  # Self-explanatory.

def set_clipboard(url_list):
    for url in url_list:
        pyperclip.copy(url)
    spam = pyperclip.paste()

def unix_main():
    if len(sys.argv) > 1:
        url_list = []
        for i in sys.argv[1:]:
            myThread(i).start()
        sys.exit(-1)
    print "running ... ... \nPress Ctr+C to Stop"
    observer = Observer()
    observer.schedule(MyHandler(), path=path_to_watch if path_to_watch else '.', recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

def main():
    unix_main()   #mac 下执行

if __name__ == "__main__":
    main()
