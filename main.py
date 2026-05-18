import mss 
import numpy as np
import cv2 as cv
import time
import pygetwindow as gw
import pyautogui
from threading import Thread


class ScreenCapture:
    '''专门负责屏幕捕获的类（单一职责原则）'''
    def __init__(self, window_title='魔兽世界'):
        self.window_title = window_title    # 要捕获的窗口标题，默认为'魔兽世界'
        self.sct = mss.mss()        # 创建mss对象，用于屏幕捕获
        self.window = None          # 存储捕捉到的窗口对象，初始化默认为None
        self.bbox = None            # 存储捕捉到的窗口位置和大小的变量，初始化默认为None
        self.cur_img = None         # 存储当前捕获的图像（BGR格式），初始化默认为None
        self.cur_imgHSV = None      # 存储当前捕获的图像（HSV格式），初始化默认为None
        self.running = False        # 标志位，指示捕获线程是否正在运行，初始化默认为False
        self.thread = None          # 存储捕获线程对象，初始化默认为None

    def select_window(self) -> bool:
        '''选择要捕获的窗口'''
        try:
            windows = gw.getWindowsWithTitle(self.window_title) # 获取窗口对象
            if not windows:
                print(f"未找到标题为 '{self.window_title}' 的窗口。")
                return False
            
            self.window = windows[0]    # 选择第一个匹配的窗口, 把窗口对象存储在self.window中
            self.window.activate()      # 激活窗口，确保它在前台
            print(f"已选择窗口: '{self.window_title}'")
            return True
        except Exception as e:
            print(f"选择窗口时发生错误: {e}")
            return False

    def _update_bbox(self):
        '''更新窗口位置和大小'''
        if self.window:
            self.bbox = {
                'left': self.window.left,
                'top': self.window.top,
                'width': self.window.width,
                'height': self.window.height
            }

    def start_capture(self):
        '''启动屏幕捕获线程'''
        if self.running:
            return 
        self.running = True
        self.thread = Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
        print("屏幕捕获已启动。")

    def stop_capture(self):
        '''停止屏幕捕获线程'''
        self.running = False
        if self.thread:
            self.thread.join()
            print("屏幕捕获已停止。")

    def _capture_loop(self):
        '''主循环，持续捕获屏幕'''
        print("正在捕获屏幕...")
        while self.running:
            try:
                if not self.window or not self.bbox:    # 如果没有窗口或bbox，尝试重新选择窗口和更新bbox
                    time.sleep(0.5)
                    continue

                self._update_bbox() # 更新窗口位置和大小

                img = np.array(self.sct.grab(self.bbox)) # 捕获屏幕并转换为numpy数组
                self.cur_img = cv.cvtColor(img, cv.COLOR_BGRA2BGR) # 转换为BGR格式
                self.cur_imgHSV = cv.cvtColor(self.cur_img, cv.COLOR_BGR2HSV) # 转换为HSV格式

                time.sleep(0.05) # 控制捕获频率

            except Exception as e:
                print(f"捕获屏幕时发生错误: {e}")
                time.sleep(1) # 发生错误时等待一段时间后重试

if __name__ == "__main__":
    capture = ScreenCapture(window_title='魔兽世界')

    if capture.select_window():
        capture.start_capture()

        try:
            print("按 Ctrl+C 停止捕获...")
            while True:
                time.sleep(1) # 主线程保持运行，捕获线程在后台工作
                if capture.cur_img is not None:
                    # 这里可以添加对cur_img的处理逻辑，例如显示或保存
                    print(f'当前捕获的图像大小: {capture.cur_img.shape}')
        except KeyboardInterrupt:
            print("正在停止捕获...")
            capture.stop_capture()
        
