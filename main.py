import mss
import numpy as np
import cv2 as cv
import time
import pygetwindow as gw
import pyautogui
from threading import Thread


class ScreenCapture:
    def __init__(self, window_title="魔兽世界"):
        self.window_title = window_title
        self.sct = mss.mss()
        self.window = None
        self.bbox = None
        self.cur_img = None
        self.cur_imgHSV = None
        self.running = False
        self.thread = None

    def select_window(self) -> bool:
        try:
            windows = gw.getWindowsWithTitle(self.window_title)
            if not windows:
                print(f"❌ 未找到窗口: {self.window_title}")
                return False
            self.window = windows[0]
            self.window.activate()
            self._update_bbox()
            print(f"✅ 已选中窗口: {self.window.title}")
            return True
        except Exception as e:
            print(f"窗口选择失败: {e}")
            return False

    def _update_bbox(self):
        if self.window:
            self.bbox = {"top": self.window.top, "left": self.window.left,
                        "width": self.window.width, "height": self.window.height}

    def start_capture(self):
        if self.running: return
        self.running = True
        self.thread = Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
        print("📸 屏幕捕捉已启动")

    def _capture_loop(self):
        while self.running:
            try:
                if not self.bbox: 
                    time.sleep(0.5)
                    continue
                self._update_bbox()
                img = np.array(self.sct.grab(self.bbox))
                self.cur_img = cv.cvtColor(img, cv.COLOR_BGRA2BGR)
                self.cur_imgHSV = cv.cvtColor(self.cur_img, cv.COLOR_BGR2HSV)
                time.sleep(0.05)
            except:
                time.sleep(0.5)

    def stop_capture(self):
        self.running = False


class FishingAgent:
    def __init__(self, screen_capture: ScreenCapture):
        self.screen = screen_capture
        self.running = False
        self.fishing_thread = None
        self.template = None
        self.load_template()
        self.cast_key = '1'

    def load_template(self):
        try:
            self.template = cv.imread("assets/fishing_bobber.png")
            if self.template is not None:
                print(f"✅ 浮标模板加载成功 | 尺寸: {self.template.shape}")
            else:
                print("⚠️ 未能加载浮标模板")
        except Exception as e:
            print(f"加载模板失败: {e}")

    def cast_lure(self):
        try:
            print(f"🎣 施法 - 按下 {self.cast_key} 键")
            pyautogui.press(self.cast_key)
            time.sleep(1.8)        # 等待浮标落水
            return True
        except Exception as e:
            print(f"施法失败: {e}")
            return False

    def find_lure(self):
        if self.screen.cur_img is None or self.template is None:
            return None
        try:
            result = cv.matchTemplate(self.screen.cur_img, self.template, cv.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv.minMaxLoc(result)
            
            if max_val >= 0.65:        # 阈值可调
                h, w = self.template.shape[:2]
                center = (max_loc[0] + w//2, max_loc[1] + h//2)
                print(f"✅ 找到浮标！匹配度: {max_val:.3f} 位置: {center}")
                return center
            return None
        except:
            return None

    def fishing_loop(self):
        print("🎣 钓鱼循环启动...")
        while self.running:
            self.cast_lure()
            lure_pos = self.find_lure()
            if lure_pos:
                time.sleep(6)      # 后面会改成实时监控
            else:
                time.sleep(1.5)

    def start(self):
        if self.running: return
        # 增加等待，确保有图像
        for _ in range(20):        # 最多等 2 秒
            if self.screen.cur_img is not None:
                break
            time.sleep(0.1)
        
        if self.screen.cur_img is None:
            print("⚠️ 等待超时，仍未获取到图像")
            return
            
        self.running = True
        self.fishing_thread = Thread(target=self.fishing_loop, daemon=True)
        self.fishing_thread.start()
        print("🚀 FishingAgent 已启动，正在自动抛竿...")


# ====================== 主程序 ======================
if __name__ == "__main__":
    screen = ScreenCapture("魔兽世界")
    agent = FishingAgent(screen)

    if screen.select_window():
        screen.start_capture()
        time.sleep(2.0)           # 给屏幕捕捉更多启动时间
        
        agent.start()             # 启动钓鱼

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n正在退出...")
        finally:
            agent.stop() if hasattr(agent, 'stop') else None
            screen.stop_capture()
