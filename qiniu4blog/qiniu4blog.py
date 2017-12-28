#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os, time, sys, ConfigParser, platform, urllib, qiniu, pyperclip, signal, threading
from mimetypes import MimeTypes
from os.path import expanduser
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler


# 使用watchdog 监控文件夹中的图像
class MyHandler(PatternMatchingEventHandler):
    patterns = ["*.jpeg", "*.jpg", "*.png", "*.bmp", "*.gif","*.tiff"]
    ignore_directories = True
    case_sensitive = False
    def process(self, event):
        if event.event_type == 'created'or event.event_type == 'modified': #如果是新增文件或修改的文件
            myThread(event.src_path, 1).start() # 开启线程
    def on_modified(self, event):
        self.process(event)
    def on_created(self, event):
        self.process(event)


# 使用多线程上传
class myThread(threading.Thread):
    def __init__(self, filePath, mode): #filePath 文件路径 和 上传模式
        threading.Thread.__init__(self)
        self.filePath = filePath
        self.mode = mode
    def run(self):
        threadLock.acquire()
        job(self.filePath, self.mode)
        threadLock.release()


# 上传图像、复制到粘贴板、写到文件
def job(file, mode):
    if mode == 1:
        url = upload_with_full_Path(file)
    if mode == 2:
        url = upload_with_full_Path_cmd(file)
    pyperclip.copy(url)
    pyperclip.paste()
    print url
    with open('MARKDOWN_FORMAT_URLS.txt', 'a') as f:
        image = '![' + url + ']' + '(' + url + ')' + '\n'
        f.write(image + '\n')

#-----------------配置--------------------
#homedir = expanduser("~")  # 获取用户主目录
config = ConfigParser.RawConfigParser()
config.read('qiniu.cfg')  # 读取配置文件
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
    if enable == 'false':
        print 'custom_url not set'
    else:
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
def upload_without_key(bucket, filePath, uploadname):
    auth = qiniu.Auth(accessKey, secretKey)
    upToken = auth.upload_token(bucket, key=None)
    key = uploadname
    retData, respInfo = qiniu.put_file(upToken, key, filePath, mime_type=mime.guess_type(filePath)[0])
    parseRet(retData, respInfo)


# 上传文件方式 2
def upload_with_full_Path(filePath):
    if platform.system() == 'Windows':
        fileName = "/".join("".join(filePath.rsplit(path_to_watch))[1:].split("\\"))
    else:
        fileName = "".join(filePath.rsplit(path_to_watch))[1:]
    upload_without_key(bucket, filePath, fileName.decode(setCodeingByOS()))
    if enable == 'true':
        return addr + urllib.quote(fileName.decode(setCodeingByOS()).encode('utf-8'))
    else:
        return 'http://' + bucket + '.qiniudn.com/' + urllib.quote(fileName.decode(setCodeingByOS()).encode('utf-8'))


# 上传文件方式 3
def upload_with_full_Path_cmd(filePath):
    if platform.system() == 'Windows':
        fileName = os.path.basename("/".join((filePath.split("\\"))))
    else:
        fileName = os.path.basename(filePath)
    upload_without_key(bucket, filePath, fileName.decode(setCodeingByOS()))
    if enable == 'true':
        return addr + urllib.quote(fileName.decode(setCodeingByOS()).encode('utf-8'))
    else:
        return 'http://' + bucket + '.qiniudn.com/' + urllib.quote(fileName.decode(setCodeingByOS()).encode('utf-8'))

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

def window_main():
    if len(sys.argv) > 1:
        url_list = []
        for i in sys.argv[1:]:
            url_list.append(upload_with_full_Path_cmd(i))
        with open('MARKDOWN_FORMAT_URLS.txt', 'a') as f:
            for url in url_list:
                image = '![' + url + ']' + '(' + url + ')' + '\n'
                print url, '\n'
                f.write(image)
        print "\nNOTE: THE MARKDOWN FORMAT URLS ALREADY SAVED IN MARKDOWN_FORMAT_URLS.txt FILE"
        set_clipboard(url_list)
        sys.exit(-1)
    print "running ... ... \nPress Ctr+C to Stop"
    before = get_filepaths(path_to_watch)
    while 1:
        time.sleep(1)
        after = get_filepaths(path_to_watch)
        added = [f for f in after if not f in before]
        removed = [f for f in before if not f in after]
        if added:
            url_list = []
            for i in added:
                url_list.append(upload_with_full_Path(i))
            with open('MARKDOWN_FORMAT_URLS.txt', 'a') as f:
                for url in url_list:
                    image = '![' + url + ']' + '(' + url + ')' + '\n'
                    print url, '\n'
                    f.write(image)
            print "\nNOTE: THE MARKDOWN FORMAT URLS ALREADY SAVED IN MARKDOWN_FORMAT_URLS.txt FILE"
            set_clipboard(url_list)
        if removed:
            pass
        before = after


def unix_main():
    if len(sys.argv) > 1:
        url_list = []
        for i in sys.argv[1:]:
            myThread(i, 2).start()
        sys.exit(-1)
    print "running ... ... \nPress Ctr+C to Stop"
    observer = Observer()
    observer.schedule(MyHandler(), path=path_to_watch if path_to_watch else '.', recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

def main():
    if os.name == 'nt' or platform.system() == 'Windows':
        window_main()  #window 下执行
    else:
        unix_main()   #mac 下执行

if __name__ == "__main__":
    main()
