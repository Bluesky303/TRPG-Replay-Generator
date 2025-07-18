#!/usr/bin/env python
# coding: utf-8

# 图形界面的欢迎窗口，显示在主界面之前


import sys
import ttkbootstrap as ttk
from PIL import Image, ImageTk


from typing import TYPE_CHECKING
from typing import Tuple
if TYPE_CHECKING:
    from multiprocessing.connection import Connection


class RplGenStudioWelcome(ttk.Window):
    # 初始化
    def __init__(self, mulitproc_connect: 'Connection', pic_width=800, pic_height=450, fade_speed: float = 0.04, sleep_time: int = 2000):
        # 获取尺寸
        self.scale_size, self.screen_width, self.screen_height = self.get_scale_size()
        window_width = int(pic_width*self.scale_size)
        window_height = int(pic_height*self.scale_size)
        
        # 多进程的信号
        self.pipe = mulitproc_connect
        
        # 窗口位置为居中
        x = int((self.screen_width/2) - (window_width/2))
        y = int((self.screen_height/2) - (window_height/2))

        super().__init__(
            resizable = (False,False),
            size = (window_width, window_height),
            position = (x, y),
            overrideredirect = True,
        )
        
        # 画面
        self.image = ImageTk.PhotoImage(name='welcome',image=Image.open('./assets/cover.jpg').resize([window_width,window_height]))
        self.image_show = ttk.Label(master=self,image='welcome',borderwidth=0,anchor='center',background='#963fff')
        self.image_show.pack(fill='both',expand=True)
        
        # 主循环
        self.fade_speed = fade_speed
        self.sleep_time = sleep_time
        self.attributes('-alpha', 0)
        self.fade_in()
        self.mainloop()
        
    def get_scale_size(self)->Tuple[float, int, int]:
        """Get scale size and screen size of current system.

        Returns:
            Tuple[float, int, int]: (scale_size, screen_width, screen_height)
        """
        def windows_scale_size():
            try:
                from ctypes import windll
                
                scale_size = windll.shcore.GetScaleFactorForDevice(0) / 100
                screen_width = int(windll.user32.GetSystemMetrics(0) * scale_size)
                screen_height = int(windll.user32.GetSystemMetrics(1) * scale_size)
                
                return scale_size, screen_width, screen_height
            except Exception:
                print('Cannot get scale factor, Using default value')
                return 1, 1920, 1080 
        def macos_scale_size():
            return 2.0, 2560, 1600
            
        platform = sys.platform
        handler = {
            'win32': windows_scale_size,
            'darwin': macos_scale_size,
            # 'linux': linux_scale_size,
        }

        return handler[platform]()
    
    def fade_out(self):
        alpha = self.attributes('-alpha')
        if alpha > 0:
            alpha -= self.fade_speed
            self.attributes('-alpha', alpha)
            self.after(20, self.fade_out)
        else:
            self.destroy()
            
    def fade_in(self):
        alpha = self.attributes('-alpha')
        if alpha < 1:
            alpha += self.fade_speed
            self.attributes('-alpha', alpha)
            self.after(20, self.fade_in)
        else:
            self.after(self.sleep_time, self.check_pipe)
    # 检查信号
    def check_pipe(self):
        # 如果接收到了信号
        if self.pipe.poll():
            msg = self.pipe.recv()
            if msg == 'terminate':
                # 淡出
                self.fade_out()
        self.after(100, self.check_pipe)



def show_welcome(*args, **kwargs):
    welcome = RplGenStudioWelcome(*args, **kwargs)
    pass

if __name__ == '__main__':
    import multiprocessing
    multiprocessing.freeze_support()
    
    parent_conn, child_conn = multiprocessing.Pipe()
    show_welcome_process = multiprocessing.Process(target=show_welcome, args=(child_conn, ), kwargs={'fade_speed': 0.1, 'sleep_time': 100})
    show_welcome_process.start()
    
    parent_conn.send('terminate')
    show_welcome_process.join()