import time
from threading import Thread

import cv2 as cv
import mss
import numpy as np
import pyautogui
import pygetwindow as gw


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
            time.sleep(0.5)

            self._update_bbox()

            print(f"✅ 已选中窗口: {self.window.title}")
            print(f"窗口位置: left={self.window.left}, top={self.window.top}")
            print(f"窗口大小: width={self.window.width}, height={self.window.height}")

            return True

        except Exception as e:
            print(f"窗口选择失败: {e}")
            return False

    def _update_bbox(self):
        if self.window:
            self.bbox = {
                "top": self.window.top,
                "left": self.window.left,
                "width": self.window.width,
                "height": self.window.height,
            }

    def start_capture(self):
        if self.running:
            return

        self.running = True
        self.thread = Thread(target=self._capture_loop, daemon=True)
        self.thread.start()

        print("✅ 屏幕捕捉已启动")

    def _capture_loop(self):
        while self.running:
            try:
                if not self.bbox:
                    time.sleep(0.5)
                    continue

                self._update_bbox()

                img = np.array(self.sct.grab(self.bbox))

                # mss 截图是 BGRA，转成 BGR 给 OpenCV 用
                self.cur_img = cv.cvtColor(img, cv.COLOR_BGRA2BGR)
                self.cur_imgHSV = cv.cvtColor(self.cur_img, cv.COLOR_BGR2HSV)

                time.sleep(0.05)

            except Exception as e:
                print(f"截图失败: {e}")
                time.sleep(0.5)

    def stop_capture(self):
        self.running = False
        print("⛔ 屏幕捕捉已停止")


class FishingAgent:
    def __init__(self, screen_capture: ScreenCapture):
        self.screen = screen_capture

        self.running = False
        self.fishing_thread = None

        self.cast_key = "1"

        self.template_path = "assets/fishing_bobber.png"
        self.template = None
        self.template_h = 0
        self.template_w = 0
        self.load_template()

        # 状态机
        self.state = "IDLE"

        self.cast_time = 0
        self.state_enter_time = time.time()

        # 鱼漂相关
        self.lure_position = None
        self.stable_position = None
        self.last_match_value = 0

        # 参数：你以后主要调这里
        self.match_threshold = 0.62

        # 抛竿后多久开始找鱼漂
        self.after_cast_delay = 2.5

        # 找到鱼漂后，再等多久开始判断咬钩
        self.bite_detect_delay = 3.0

        # 一轮钓鱼最长等待时间
        self.max_wait_time = 28.0

        # 鱼漂移动多少像素，认为咬钩
        self.bite_move_threshold = 10

        # 防止误判：连续检测到几次移动才收杆
        self.bite_confirm_need = 2
        self.bite_confirm_count = 0

        # 调试输出控制
        self.last_debug_time = 0

    def load_template(self):
        self.template = cv.imread(self.template_path, cv.IMREAD_COLOR)

        if self.template is None:
            print(f"❌ 未找到模板: {self.template_path}")
            print("请确认文件存在：assets/fishing_bobber.png")
            return

        self.template_h, self.template_w = self.template.shape[:2]

        print(f"✅ 模板加载成功: {self.template_path}")
        print(f"模板尺寸: {self.template_w}x{self.template_h}")

    def set_state(self, new_state):
        self.state = new_state
        self.state_enter_time = time.time()
        print(f"➡️ 状态切换: {new_state}")

    def cast_lure(self):
        try:
            print(f"🎣 抛竿：按下 {self.cast_key}")

            # 每次抛竿前清空上一轮数据
            self.lure_position = None
            self.stable_position = None
            self.last_match_value = 0
            self.bite_confirm_count = 0

            pyautogui.press(self.cast_key)

            self.cast_time = time.time()
            self.set_state("CASTING")

            return True

        except Exception as e:
            print(f"❌ 抛竿失败: {e}")
            self.set_state("IDLE")
            return False

    def find_lure(self):
        if self.screen.cur_img is None:
            return None

        if self.template is None:
            return None

        try:
            result = cv.matchTemplate(
                self.screen.cur_img,
                self.template,
                cv.TM_CCOEFF_NORMED,
            )

            _, max_val, _, max_loc = cv.minMaxLoc(result)
            self.last_match_value = max_val

            if max_val < self.match_threshold:
                return None

            center_x = max_loc[0] + self.template_w // 2
            center_y = max_loc[1] + self.template_h // 2

            self.lure_position = (center_x, center_y)

            return self.lure_position

        except Exception as e:
            print(f"❌ 模板匹配失败: {e}")
            return None

    def distance(self, p1, p2):
        if not p1 or not p2:
            return 0

        dx = p1[0] - p2[0]
        dy = p1[1] - p2[1]

        return (dx * dx + dy * dy) ** 0.5

    def is_bite(self):
        """
        判断是否咬钩。

        这里不用固定亮度判断。
        先记录鱼漂稳定位置 stable_position。
        后面如果鱼漂位置突然明显移动，认为可能咬钩。
        """

        if not self.lure_position:
            return False

        # 找到鱼漂后，前几秒不判断咬钩
        if time.time() - self.state_enter_time < self.bite_detect_delay:
            return False

        if self.stable_position is None:
            self.stable_position = self.lure_position
            print(f"📌 记录鱼漂基准位置: {self.stable_position}")
            return False

        move_distance = self.distance(self.lure_position, self.stable_position)

        now = time.time()
        if now - self.last_debug_time > 1:
            print(
                f"监控中 | 匹配度={self.last_match_value:.3f} "
                f"| 当前={self.lure_position} "
                f"| 基准={self.stable_position} "
                f"| 移动={move_distance:.1f}px "
                f"| 确认={self.bite_confirm_count}/{self.bite_confirm_need}"
            )
            self.last_debug_time = now

        if move_distance >= self.bite_move_threshold:
            self.bite_confirm_count += 1

            if self.bite_confirm_count >= self.bite_confirm_need:
                print(f"⚡ 检测到咬钩！鱼漂移动 {move_distance:.1f}px")
                return True
        else:
            # 如果移动不明显，重置确认次数
            self.bite_confirm_count = 0

            # 缓慢更新基准位置，避免水面小幅波动造成误差
            sx, sy = self.stable_position
            lx, ly = self.lure_position

            self.stable_position = (
                int(sx * 0.85 + lx * 0.15),
                int(sy * 0.85 + ly * 0.15),
            )

        return False

    def pull_line(self):
        if not self.lure_position:
            print("⚠️ 没有鱼漂坐标，无法收杆")
            return False

        if not self.screen.window:
            print("⚠️ 没有窗口信息，无法计算屏幕坐标")
            return False

        x, y = self.lure_position

        # lure_position 是窗口内部坐标
        # pyautogui 需要真实屏幕坐标，所以要加窗口 left/top
        screen_x = self.screen.window.left + x
        screen_y = self.screen.window.top + y

        print(f"🖱️ 右键收杆: 窗口坐标=({x}, {y}) 屏幕坐标=({screen_x}, {screen_y})")

        pyautogui.rightClick(screen_x, screen_y)

        return True

    def fishing_loop(self):
        print("✅ 钓鱼状态机已启动")

        while self.running:
            try:
                now = time.time()

                if self.state == "IDLE":
                    self.cast_lure()

                elif self.state == "CASTING":
                    # 抛竿后等待浮标落水
                    if now - self.cast_time >= self.after_cast_delay:
                        self.set_state("FINDING_BOBBER")

                elif self.state == "FINDING_BOBBER":
                    pos = self.find_lure()

                    if pos:
                        print(f"✅ 找到鱼漂: {pos} | 匹配度={self.last_match_value:.3f}")
                        self.stable_position = pos
                        self.set_state("WAITING_BITE")

                    elif now - self.cast_time > self.max_wait_time:
                        print("⏰ 超时仍未找到鱼漂，重新抛竿")
                        self.set_state("IDLE")

                    else:
                        # 不要每帧都打印，太吵
                        if now - self.last_debug_time > 1:
                            print(f"寻找鱼漂中... 当前最高匹配度={self.last_match_value:.3f}")
                            self.last_debug_time = now

                elif self.state == "WAITING_BITE":
                    self.find_lure()

                    if self.lure_position and self.is_bite():
                        self.pull_line()
                        self.set_state("LOOTING")

                    elif now - self.cast_time > self.max_wait_time:
                        print("⏰ 等待咬钩超时，重新抛竿")
                        self.set_state("IDLE")

                elif self.state == "LOOTING":
                    # 收杆后等一下，给游戏拾取/收杆动画时间
                    if now - self.state_enter_time >= 3.0:
                        self.set_state("IDLE")

                time.sleep(0.08)

            except Exception as e:
                print(f"❌ 钓鱼循环异常: {e}")
                time.sleep(1)
                self.set_state("IDLE")

    def start(self):
        if self.running:
            return

        if self.template is None:
            print("❌ 没有模板，无法启动")
            return

        # 等待截图线程拿到第一张图
        print("等待截图画面...")

        for _ in range(50):
            if self.screen.cur_img is not None:
                break
            time.sleep(0.1)

        if self.screen.cur_img is None:
            print("❌ 没有获取到游戏画面，无法启动")
            return

        self.running = True
        self.fishing_thread = Thread(target=self.fishing_loop, daemon=True)
        self.fishing_thread.start()

        print("✅ FishingAgent 已启动")

    def stop(self):
        self.running = False
        print("⛔ FishingAgent 已停止")


if __name__ == "__main__":
    screen = ScreenCapture("魔兽世界")
    agent = FishingAgent(screen)

    if screen.select_window():
        screen.start_capture()

        time.sleep(2.0)

        agent.start()

        try:
            while True:
                time.sleep(1)

        except KeyboardInterrupt:
            print("\n正在退出...")

        finally:
            agent.stop()
            screen.stop_capture()
