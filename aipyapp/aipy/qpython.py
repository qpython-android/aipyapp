# -*- coding: utf8; -*-
# qpy 环境相关函数
import os
import random
import string

def create_temp_py_file(code, dir):
    # 生成一个随机的文件名
    random_filename = ''.join(random.choices(string.ascii_letters + string.digits, k=10)) + '.py'
    temp_file_path = os.path.join(dir, random_filename)
    
    # 写入代码到临时文件
    with open(temp_file_path, 'w', encoding='utf-8') as temp_file:
        temp_file.write(code)
    
    return temp_file_path

def qpy_is_webapp(code):
    # 读取前128个字节
    header = code[:128]
    
    # 将字节转换为字符串并检查是否包含特定内容
    if '#qpy:webapp' in header:
        return True
    else:
        return False

def qpy_exec(code, args):
    try: # 在QPython环境跑的程序
        import qpy, androidhelper
        script = create_temp_py_file(code, qpy.tmp)
        droid = androidhelper.Android()
        droid.executeQPy(script)
    except Exception as e: # 在非QPython环境跑的程序
        exec(code, gs)
