#!/usr/bin/env python
# coding: utf-8

import multiprocessing
from src.ui.welcome import RplGenStudioWelcome

def show_welcome(*args, **kwargs):
    welcome = RplGenStudioWelcome(*args, **kwargs)
    pass

if __name__ == '__main__':
    # 多进程的支持
    multiprocessing.freeze_support()
    # 多进程启动welcome
    parent_conn, child_conn = multiprocessing.Pipe()
    show_welcome_process = multiprocessing.Process(target=show_welcome,args=(child_conn,), kwargs={'fade_speed':0.2, 'sleep_time':100})
    show_welcome_process.start()

    # 再初始化 MainWindow
    from core.GUI_MainWindow import RplGenStudioMainWindow

    # 等待
    # show_welcome_process.join()
    parent_conn.send('terminate')
    show_welcome_process.join()

    # gui的入口
    root = RplGenStudioMainWindow()
    root.mainloop()