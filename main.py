import mss 
import numpy as np
import cv2 as cv
import time
import pygetwindow as gw
import pyautogui


class MainAgent:
    def __init__(self):
        self.agents = [] # 可存放多个子Agent

        self.cur_img = None
        self.cur_imgHSV = None

        self.zone = None

    def _capture_screen_loop(self, window_title):
        with mss.mss() as sct:
            while True:
                # 获取窗口位置和大小
                window = gw.getWindowsWithTitle(window_title)[0]
                x, y, width, height = window.left, window.top, window.width, window.height

                # 定义捕获区域
                monitor = {"top": y, "left": x, "width": width, "height": height}

                # 捕获屏幕
                img = np.array(sct.grab(monitor))

                # 转换颜色空间为HSV
                self.cur_img = cv.cvtColor(img, cv.COLOR_BGRA2BGR) 
                self.cur_imgHSV = cv.cvtColor(img, cv.COLOR_BGR2HSV)

                time.sleep(0.1)  # 控制捕获频率



