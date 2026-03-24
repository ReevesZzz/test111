import streamlit as st
import requests
import json
import time
from PIL import Image
import os

# ========== API 配置（从 Secrets 读取） ==========
API_KEY = st.secrets.get("API_KEY", "your-local-test-key")
BASE_URL = "https://api.deepseek.com/v1/chat/completions"
# ===============================================

# 获取脚本所在目录（用于加载图片）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 角色设定（激励、鼓励版）
characters = {
    "汤姆": "你叫汤姆，是印刷厂里经验丰富的工人。你相信团结的力量，总是鼓励工友们争取更好的待遇。你说话充满激情，但会考虑大家的意见。",
    "玛丽": "你叫玛丽，是印刷厂里细心的女工。你善于倾听和调解，总是用温和的方式推动大家前进。你相信通过协商可以争取权益。",
    "杰克": "你叫杰克，是印刷厂的学徒，充满理想。你虽然年轻，但愿意学习，也愿意支持正确的行动。你说话真诚，容易感动。"
}

# 初始化 session state
if "state" not in st.session_state:
    st.session_state.state = {
        "汤姆": {"radical": 80, "trust": 50},
        "玛丽": {"radical": 40, "trust": 50},
        "杰克": {"radical": 60, "trust": 50}
    }
    st.session_state.messages = [
        {"role": "system", "content": "这是1848年伦敦一家印刷厂的休息时间。工人们在闲聊。"},
        {"role": "assistant", "name": "汤姆", "content": "兄弟们，我们不能再忍了！工资这么低，厂长还在加活！"}
    ]
    st.session_state.current_day = 1
    st.session_state.game_active = True
    st.session_state.logs = []
    st.session_state.waiting_for_response = False

MAX_DAYS = 7

def get_response(name, player_input=None):
    context = "\n".join([f"{m.get('name', '系统')}: {m['content']}" for m in st.session_state.messages[-6:]])
    s = st.session_state.state[name]
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
            st.session_state.state[name]["radical"] = min(100, st.session_state.state[name]["radical"] + 10)
            st.session_state.state[name]["trust"] = min(100, st.session_state.state[name]["trust"] + 5)
        elif "冷静" in player_input or "慢慢" in player_input:
            st.session_state.state[name]["radical"] = max(0, st.session_state.state[name]["radical"] - 10)
            st.session_state.state[name]["trust"] = min(100, st.session_state.state[name]["trust"] + 10)
        elif "怕" in player_input or "危险" in player_input:
            st.session_state.state[name]["radical"] = max(0, st.session_state.state[name]["radical"] - 5)
            st.session_state.state[name]["trust"] = max(0, st.session_state.state[name]["trust"] - 5)
        else:
            st.session_state.state[name]["trust"] = min(100, st.session_state.state[name]["trust"] + 2)

    return reply

def get_ending():
    avg_radical = (st.session_state.state["汤姆"]["radical"] + st.session_state.state["玛丽"]["radical"] + st.session_state.state["杰克"]["radical"]) / 3
    avg_trust = (st.session_state.state["汤姆"]["trust"] + st.session_state.state["玛丽"]["trust"] + st.session_state.state["杰克"]["trust"]) / 3
    if avg_radical >= 70 and avg_trust >= 60:
        return "罢工成功！你赢得了工人的信任，成为秘密组织的一员。工人们团结起来，厂长被迫提高工资。"
    elif avg_radical >= 70:
        return "罢工发生了，但没人信任你，你被排除在外。工人们虽然抗争，但缺乏组织，最终失败。"
    elif avg_radical <= 30:
        return "什么都没发生，一切照旧。你选择离开了印刷厂，去别处寻找机会。"
    else:
        return "罢工被镇压了，有人被捕。你在混乱中离开了伦敦，但地下组织的火种仍在燃烧。"

def run_ai_turn():
    for name in ["汤姆", "玛丽", "杰克"]:
        reply = get_response(name)
        st.session_state.logs.append(f"{name}: {reply}")
        st.session_state.messages.append({"role": "assistant", "name": name, "content": reply})
        time.sleep(0.3)
    st.session_state.waiting_for_response = True

def player_choice(action):
    if action == "罢工":
        player_words = "我支持罢工！"
    elif action == "冷静":
        player_words = "我们应该冷静下来，慢慢谈。"
    elif action == "担忧":
        player_words = "我有点害怕，这样会不会太危险？"
    else:
        player_words = "......"
    st.session_state.logs.append(f"你: {player_words}")
    st.session_state.messages.append({"role": "user", "name": "玩家", "content": player_words})

    for name in ["汤姆", "玛丽", "杰克"]:
        reply = get_response(name, player_words)
        st.session_state.logs.append(f"{name}: {reply}")
        st.session_state.messages.append({"role": "assistant", "name": name, "content": reply})
        time.sleep(0.3)

    st.session_state.current_day += 1
    if st.session_state.current_day > MAX_DAYS:
        ending = get_ending()
        st.session_state.logs.append(f"\n一周过去了...\n{ending}")
        st.session_state.game_active = False
    else:
        st.session_state.waiting_for_response = False

# ========== 页面布局 ==========
st.set_page_config(page_title="1848 伦敦印刷厂", layout="centered", page_icon="📰")

# 显示背景图（如果存在）
bg_path = os.path.join(BASE_DIR, "factory_bg.png")
if os.path.exists(bg_path):
    try:
        bg_img = Image.open(bg_path)
        st.image(bg_img, use_container_width=True, caption="1848年 伦敦印刷厂")
    except:
        st.warning("背景图片加载失败")
else:
    st.info("背景图片暂未显示，但不影响游戏体验")

st.title("📰 1848 伦敦印刷厂")
st.caption("你是一名新来的排字工，走进了工人们的休息室。")

# 显示角色头像和状态卡片（一行三个）
cols = st.columns(3)
for idx, name in enumerate(["汤姆", "玛丽", "杰克"]):
    with cols[idx]:
        # 加载头像
        avatar_path = os.path.join(BASE_DIR, f"{name}.png")
        if os.path.exists(avatar_path):
            try:
                avatar = Image.open(avatar_path)
                st.image(avatar, width=80)
            except:
                st.write("👤")
        else:
            st.write("👤")
        # 状态数值
        s = st.session_state.state[name]
        st.metric(name, value=f"激进 {s['radical']}", delta=f"信任 {s['trust']}")

# 显示对话记录
chat_container = st.container()
with chat_container:
    for log in st.session_state.logs[-40:]:
        if log.startswith("你:"):
            st.markdown(f"<div style='text-align: right; color: #1f77b4;'>{log}</div>", unsafe_allow_html=True)
        elif log.startswith("系统"):
            st.info(log)
        else:
            st.write(log)

# 游戏控制
if st.session_state.game_active:
    st.write(f"**第 {st.session_state.current_day} / {MAX_DAYS} 天**")

    if st.session_state.waiting_for_response:
        st.write("工人们聊完了，你想说什么？")
        action = st.radio("你的态度：", ["支持罢工", "建议冷静", "表达担忧", "沉默不语"], index=None, horizontal=True)
        if action:
            if action == "支持罢工":
                player_choice("罢工")
            elif action == "建议冷静":
                player_choice("冷静")
            elif action == "表达担忧":
                player_choice("担忧")
            else:
                player_choice("沉默")
            st.rerun()
    else:
        with st.spinner("工人们在交谈..."):
            run_ai_turn()
        st.rerun()
else:
    st.success("游戏结束！")
    st.write(st.session_state.logs[-1])
    if st.button("重新开始"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
