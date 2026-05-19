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
        
        # 新增：状态控制
        self.state = "IDLE"          # IDLE / CASTING / MONITORING / PULLING
        self.cast_time = 0           # 记录施法时间
        self.lure_position = None

    def load_template(self):
        try:
            self.template = cv.imread("assets/fishing_bobber.png")
            if self.template is not None:
                print(f"✅ 浮标模板加载成功 | 尺寸: {self.template.shape}")
            else:
                print("⚠️ 未能加载浮标模板图片")
        except Exception as e:
            print(f"加载模板失败: {e}")

    def cast_lure(self):
        """施法"""
        try:
            print(f"🎣 施法 - 按下 {self.cast_key} 键")
            pyautogui.press(self.cast_key)
            self.cast_time = time.time()
            self.state = "CASTING"
            time.sleep(1.8)          # 等待浮标落水
            self.state = "MONITORING"
            self.lure_position = None
            return True
        except Exception as e:
            print(f"施法失败: {e}")
            return False

    def find_lure(self):
        """寻找浮标"""
        if self.screen.cur_img is None or self.template is None:
            return None
        try:
            result = cv.matchTemplate(self.screen.cur_img, self.template, cv.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv.minMaxLoc(result)
            
            if max_val >= 0.65:
                h, w = self.template.shape[:2]
                center = (max_loc[0] + w//2, max_loc[1] + h//2)
                self.lure_position = center
                return center
            return None
        except:
            return None

    def is_bite(self):
        """判断是否咬钩（颜色检测） - 这是核心逻辑"""
        if self.lure_position is None or self.screen.cur_imgHSV is None:
            return False
            
        x, y = self.lure_position
        # 取浮标周围一小块区域检测颜色变化
        roi_size = 12
        roi = self.screen.cur_imgHSV[max(0, y-roi_size):y+roi_size, 
                                    max(0, x-roi_size):x+roi_size]
        
        if roi.size == 0:
            return False
            
        # 计算平均颜色（HSV 的 V 通道 = 亮度）
        avg_value = np.mean(roi[:, :, 2])
        
        # 咬钩时通常亮度会突然变化（不同服务器/插件表现不同）
        # 你需要根据自己的游戏画面调整这两个值
        if avg_value > 140 or avg_value < 60:        # 可调整阈值
            print(f"⚡ 检测到咬钩！平均亮度: {avg_value:.1f}")
            return True
        return False

    def pull_line(self):
        """收杆"""
        try:
            print("🎣 咬钩！正在收杆...")
            pyautogui.rightClick()          # 右键收杆（最常用）
            # pyautogui.press('2')          # 如果你用技能收杆，可以改成按键
            time.sleep(3)                   # 收杆后等待一会儿
            return True
        except Exception as e:
            print(f"收杆失败: {e}")
            return False

    def fishing_loop(self):
        """主钓鱼循环（状态机）"""
        print("🎣 钓鱼状态机已启动...")
        while self.running:
            if self.state == "IDLE" or self.state == "CASTING":
                self.cast_lure()
                
            elif self.state == "MONITORING":
                lure_pos = self.find_lure()
                
                if lure_pos:
                    self.lure_position = lure_pos
                    # 检测是否咬钩
                    if self.is_bite():
                        self.state = "PULLING"
                        self.pull_line()
                        self.state = "IDLE"       # 收杆完成后重新开始
                    else:
                        # 没咬钩，继续监控（最多监控 25 秒）
                        if time.time() - self.cast_time > 25:
                            print("⏰ 超时未咬钩，重新施法")
                            self.state = "IDLE"
                else:
                    # 没找到浮标，重新施法
                    self.state = "IDLE"
                
                time.sleep(0.15)      # 监控频率（不要太快）

    def start(self):
        if self.running: return
        # 等待图像就绪
        for _ in range(25):
            if self.screen.cur_img is not None:
                break
            time.sleep(0.1)
            
        self.running = True
        self.fishing_thread = Thread(target=self.fishing_loop, daemon=True)
        self.fishing_thread.start()
        print("🚀 FishingAgent 已启动（状态机模式）")

    def stop(self):
        self.running = False
        print("⛔ FishingAgent 已停止")


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
