import tkinter as tk
from tkinter import scrolledtext, messagebox
import threading
import time
import requests
import json
from PIL import Image, ImageTk
import os

# ========== 你的 API 配置 ==========
API_KEY = "sk-2dd8d6195e0649a3ba23efd6661d89d6"          # 替换成你的
BASE_URL = "https://api.deepseek.com/v1/chat/completions"
# ===================================

# 获取脚本所在目录（保证图片路径正确）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 角色设定（激励、鼓励版）
characters = {
    "汤姆": "你叫汤姆，是印刷厂里经验丰富的工人。你相信团结的力量，总是鼓励工友们争取更好的待遇。你说话充满激情，但会考虑大家的意见。",
    "玛丽": "你叫玛丽，是印刷厂里细心的女工。你善于倾听和调解，总是用温和的方式推动大家前进。你相信通过协商可以争取权益。",
    "杰克": "你叫杰克，是印刷厂的学徒，充满理想。你虽然年轻，但愿意学习，也愿意支持正确的行动。你说话真诚，容易感动。"
}

# 状态
state = {
    "汤姆": {"radical": 80, "trust": 50},
    "玛丽": {"radical": 40, "trust": 50},
    "杰克": {"radical": 60, "trust": 50}
}

# 对话历史
messages = [
    {"role": "system", "content": "这是1848年伦敦一家印刷厂的休息时间。工人们在闲聊。"},
    {"role": "assistant", "name": "汤姆", "content": "兄弟们，我们不能再忍了！工资这么低，厂长还在加活！"}
]

current_day = 1
MAX_DAYS = 7

def get_response(name, player_input=None):
    context = "\n".join([f"{m.get('name', '系统')}: {m['content']}" for m in messages[-6:]])
    s = state[name]
    prompt = f"""{characters[name]}

你当前的状态：
- 激进程度: {s['radical']}/100
- 对玩家(新来的排字工)的信任度: {s['trust']}/100

这是刚才的对话：
{context}

现在{name}要说话了。记住你的状态会影响你说话的语气和立场。只说一句话，直接说出来："""

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 100,
        "temperature": 0.7
    }
    try:
        response = requests.post(BASE_URL, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        reply = data['choices'][0]['message']['content']
    except Exception as e:
        reply = f"(API错误: {e})"

    if player_input:
        if "罢工" in player_input:
            state[name]["radical"] = min(100, state[name]["radical"] + 10)
            state[name]["trust"] = min(100, state[name]["trust"] + 5)
        elif "冷静" in player_input or "慢慢" in player_input:
            state[name]["radical"] = max(0, state[name]["radical"] - 10)
            state[name]["trust"] = min(100, state[name]["trust"] + 10)
        elif "怕" in player_input or "危险" in player_input:
            state[name]["radical"] = max(0, state[name]["radical"] - 5)
            state[name]["trust"] = max(0, state[name]["trust"] - 5)
        else:
            state[name]["trust"] = min(100, state[name]["trust"] + 2)

    return reply

def get_ending():
    avg_radical = (state["汤姆"]["radical"] + state["玛丽"]["radical"] + state["杰克"]["radical"]) / 3
    avg_trust = (state["汤姆"]["trust"] + state["玛丽"]["trust"] + state["杰克"]["trust"]) / 3
    if avg_radical >= 70 and avg_trust >= 60:
        return "罢工成功！你赢得了工人的信任，成为秘密组织的一员。工人们团结起来，厂长被迫提高工资。"
    elif avg_radical >= 70:
        return "罢工发生了，但没人信任你，你被排除在外。工人们虽然抗争，但缺乏组织，最终失败。"
    elif avg_radical <= 30:
        return "什么都没发生，一切照旧。你选择离开了印刷厂，去别处寻找机会。"
    else:
        return "罢工被镇压了，有人被捕。你在混乱中离开了伦敦，但地下组织的火种仍在燃烧。"

class GameApp:
    def __init__(self, root):
        self.root = root
        root.title("1848 伦敦印刷厂 - 历史沙盒")
        root.geometry("1000x750")
        root.configure(bg="#d9c8a9")

        self.canvas = tk.Canvas(root, width=1000, height=400, bg="#c7b28b", highlightthickness=0)
        self.canvas.pack(pady=10, padx=10)

        self.load_images()
        self.draw_scene()

        self.char_positions = {
            "汤姆": (200, 200),
            "玛丽": (500, 200),
            "杰克": (800, 200)
        }

        self.char_images = {}
        self.char_texts = {}
        self.char_status_tags = {}

        for name, pos in self.char_positions.items():
            x, y = pos
            if name in self.avatars:
                img = self.avatars[name]
                self.char_images[name] = self.canvas.create_image(x, y, image=img, tags=("avatar", name))
            self.char_texts[name] = self.canvas.create_text(x, y+60, text=name, font=("黑体", 14, "bold"), fill="#3a2a1a", tags=("name", name))

        # 状态面板
        self.status_frame = tk.Frame(root, bg="#e8dcc0", relief=tk.RIDGE, bd=2)
        self.status_frame.pack(pady=5, padx=10, fill=tk.X)
        self.status_labels = {}
        for name in ["汤姆", "玛丽", "杰克"]:
            frame = tk.Frame(self.status_frame, bg="#e8dcc0")
            frame.pack(side=tk.LEFT, padx=20, pady=5)
            tk.Label(frame, text=name, font=("黑体", 14, "bold"), bg="#e8dcc0", fg="#3a2a1a").pack()
            self.status_labels[name] = tk.Label(frame, text=f"激进: {state[name]['radical']}  信任: {state[name]['trust']}",
                                                font=("宋体", 10), bg="#e8dcc0")
            self.status_labels[name].pack()

        # 对话显示区域
        self.dialog_area = scrolledtext.ScrolledText(root, width=90, height=12, font=("宋体", 11), bg="#fef7e0", fg="#2c2c2c")
        self.dialog_area.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)
        self.dialog_area.config(state=tk.DISABLED)

        # 按钮
        button_frame = tk.Frame(root, bg="#d9c8a9")
        button_frame.pack(pady=10)
        self.buttons = []
        options = [("支持罢工", "罢工"), ("建议冷静", "冷静"), ("表达担忧", "担忧"), ("沉默不语", "沉默")]
        for text, action in options:
            btn = tk.Button(button_frame, text=text, width=12, command=lambda a=action: self.player_action(a),
                            bg="#b98c5f", fg="white", font=("黑体", 12))
            btn.pack(side=tk.LEFT, padx=10)
            self.buttons.append(btn)

        self.day_label = tk.Label(root, text=f"第 {current_day} / {MAX_DAYS} 天", font=("黑体", 12), bg="#d9c8a9")
        self.day_label.pack(pady=5)

        self.log_message("你是一名新来的排字工，走进了工人们的休息室。")
        self.run_ai_turn()

    def load_images(self):
        """加载图片（使用绝对路径）"""
        bg_path = os.path.join(BASE_DIR, "factory_bg.png")
        try:
            pil_bg = Image.open(bg_path)
            pil_bg = pil_bg.resize((1000, 400), Image.Resampling.LANCZOS)
            self.bg_image = ImageTk.PhotoImage(pil_bg)
        except Exception as e:
            print("背景图片加载失败，使用默认背景。", e)
            self.bg_image = None

        self.avatars = {}
        for name in ["汤姆", "玛丽", "杰克"]:
            img_path = os.path.join(BASE_DIR, f"{name}.png")
            try:
                pil_img = Image.open(img_path).convert("RGBA")
                pil_img = pil_img.resize((70, 70), Image.Resampling.LANCZOS)
                self.avatars[name] = ImageTk.PhotoImage(pil_img)
            except Exception as e:
                print(f"{name}头像加载失败，使用圆形代替。", e)
                self.avatars[name] = None

    def draw_scene(self):
        self.canvas.delete("background")
        if self.bg_image:
            self.canvas.create_image(0, 0, image=self.bg_image, anchor=tk.NW, tags="background")
        else:
            self.canvas.create_rectangle(0, 0, 1000, 400, fill="#b59a6b", outline="", tags="background")
            self.canvas.create_rectangle(50, 50, 150, 130, fill="#f5e6d3", outline="#5a3e1a", width=2, tags="background")
            self.canvas.create_rectangle(850, 50, 950, 130, fill="#f5e6d3", outline="#5a3e1a", width=2, tags="background")
            self.canvas.create_rectangle(400, 180, 600, 260, fill="#7a5a3a", outline="#3a2a1a", width=2, tags="background")

    def update_canvas_status(self):
        for name, pos in self.char_positions.items():
            x, y = pos
            if name in self.char_status_tags:
                self.canvas.delete(self.char_status_tags[name])
            rad = state[name]["radical"]
            tr = state[name]["trust"]
            text = f"激:{rad} 信:{tr}"
            tag = self.canvas.create_text(x, y+95, text=text, font=("宋体", 10), fill="#2c2c2c", tags=("status", name))
            self.char_status_tags[name] = tag

    def log_message(self, msg, speaker=None):
        self.dialog_area.config(state=tk.NORMAL)
        if speaker:
            self.dialog_area.insert(tk.END, f"{speaker}: {msg}\n")
        else:
            self.dialog_area.insert(tk.END, f"{msg}\n")
        self.dialog_area.see(tk.END)
        self.dialog_area.config(state=tk.DISABLED)

    def update_status(self):
        for name in state:
            self.status_labels[name].config(text=f"激进: {state[name]['radical']}  信任: {state[name]['trust']}")
        self.update_canvas_status()

    def run_ai_turn(self):
        def task():
            for name in ["汤姆", "玛丽", "杰克"]:
                reply = get_response(name)
                # 确保在主线程更新 UI
                self.root.after(0, self.log_message, reply, name)
                messages.append({"role": "assistant", "name": name, "content": reply})
                time.sleep(0.5)
            self.root.after(0, lambda: self.set_buttons_state(tk.NORMAL))
        self.set_buttons_state(tk.DISABLED)
        threading.Thread(target=task, daemon=True).start()

    def player_action(self, action):
        self.set_buttons_state(tk.DISABLED)
        if action == "罢工":
            player_words = "我支持罢工！"
        elif action == "冷静":
            player_words = "我们应该冷静下来，慢慢谈。"
        elif action == "担忧":
            player_words = "我有点害怕，这样会不会太危险？"
        else:
            player_words = "......"
        self.log_message(player_words, "你")
        messages.append({"role": "user", "name": "玩家", "content": player_words})

        def task():
            global current_day
            for name in ["汤姆", "玛丽", "杰克"]:
                reply = get_response(name, player_words)
                self.root.after(0, self.log_message, reply, name)
                messages.append({"role": "assistant", "name": name, "content": reply})
                time.sleep(0.5)
            self.root.after(0, self.update_status)
            current_day += 1
            self.root.after(0, self.day_label.config, {"text": f"第 {current_day} / {MAX_DAYS} 天"})
            if current_day > MAX_DAYS:
                ending = get_ending()
                self.root.after(0, self.log_message, f"\n一周过去了...\n{ending}")
                self.root.after(0, lambda: messagebox.showinfo("结局", ending))
                self.root.after(0, self.root.quit)
            else:
                self.root.after(0, self.run_ai_turn)
        threading.Thread(target=task, daemon=True).start()

    def set_buttons_state(self, state):
        for btn in self.buttons:
            btn.config(state=state)

if __name__ == "__main__":
    root = tk.Tk()
    app = GameApp(root)
    root.mainloop()
