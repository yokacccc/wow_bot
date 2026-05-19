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

class FishingAgent:
    '''钓鱼Agent类 - 负责钓鱼的具体行为'''
    def __init__(self, screen_capture: ScreenCapture):
        self.screen = screen_capture        # 接收ScreenCapture实例，便于访问捕获的图像数据
        self.running = False                    # 标志位，指示钓鱼线程是否正在运行，初始化默认为False
        self.fishing_thread = None                 # 存储钓鱼线程对象，初始化默认为None

        # 加载模板图片（浮标）
        self.template = None
        self.load_template()

        # 按键设置（可以根据需要调整）
        self.cast_key = '1'  # 施放钓鱼技能的按键

    def load_template(self):
        '''加载模板图片（浮标）'''
        try:
            self.template = cv.imread('assets\\fishing_bobber.png')
            if self.template is None:
                print("未找到模板图片 'assets\\fishing_bobber.png'，请确保路径正确。")
            else:
                print("模板图片加载成功。")
        except Exception as e:
            print(f"加载模板图片时发生错误: {e}")

    def cast_lure(self):
        '''施法 - 放下鱼竿'''
        try:
            pyautogui.press(self.cast_key) # 模拟按键施法
            time.sleep(1.5) # 等待施法动画完成
            return True
        except Exception as e:
            print(f"施法时发生错误: {e}")
            return False

    def find_lure(self):
        '''使用模板匹配寻找浮标'''
        if self.screen.cur_img is None or self.template is None:
            return None

        try: 
            # 执行模板匹配
            res = cv.matchTemplate(
                self.screen.cur_img, 
                self.template, 
                cv.TM_CCOEFF_NORMED
            )

            # 获取匹配度最高的位置
            min_val, max_val, min_loc, max_loc = cv.minMaxLoc(res)

            # 设置一个匹配度阈值，只有超过这个值才认为找到了浮标
            threshold = 0.7

            if max_val >= threshold:
                # 计算浮标中心位置
                h, w = self.tenmplate.shape[:2]
                center_x = max_loc[0] + w // 2
                center_y = max_loc[1] + h // 2

                print(f"找到浮标，位置: ({center_x}, {center_y}), 匹配度: {max_val:.2f}")
                return (center_x, center_y)
            else:
                print(f"未找到浮标，最高匹配度: {max_val:.2f}")
                return None

        except Exception as e:
            print(f"寻找浮标时发生错误: {e}")
            return None

    def start(self):
        '''启动钓鱼线程'''
        if self.running:
            return 
        if self.screen.cur_img is None:
            print('请先启动屏幕捕捉')
            return

        self.running = True
        self.fishing_thread = Thread(target=self.fishing_loop, daemon=True)
        self.fishing_thread.start()
        print("钓鱼已启动。")

    def stop(self):
        '''停止钓鱼线程'''
        self.running = False
        if self.fishing_thread:
            self.fishing_thread.join()
            print("钓鱼已停止。")

if __name__ == "__main__":
    # 1. 创建屏幕捕捉
    screen = ScreenCapture(window_title='魔兽世界')

    # 2. 创建钓鱼Agent
    agent = FishingAgent(screen)

    if screen.select_window(): # 选择窗口成功后启动捕捉和钓鱼
        screen.start_capture() # 启动屏幕捕捉
        time.sleep(2) # 等待几秒钟让捕捉线程稳定下来

        # 启动钓鱼Agent
        agent.start()         

        print('\n' + '='*50)
        print('操作说明：')
        print(' F - 手动启动钓鱼（已经自动开启）') 
        print(' Q - 停止钓鱼')
        print(' Ctrl+C - 退出程序')
        print('='*50)

        try:
            while True:
                time.sleep(0.5) # 主线程保持运行，等待用户手动停止
        except KeyboardInterrupt:
            print("正在关闭...")
            agent.stop()          # 停止钓鱼Agent
            screen.stop_capture() # 停止屏幕捕捉