import streamlit as st
import requests
import json
import time
from PIL import Image
import os

# ========== 你的 API 配置 ==========
API_KEY = st.secrets.get("API_KEY", "your-local-test-key")          # 替换成你的
BASE_URL = "https://api.deepseek.com/v1/chat/completions"
# ===================================

# 获取脚本所在目录（用于加载图片）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 角色设定（激励、鼓励版）
characters = {
    "汤姆": "你叫汤姆，是印刷厂里经验丰富的工人。你相信团结的力量，总是鼓励工友们争取更好的待遇。你说话充满激情，但会考虑大家的意见。",
    "玛丽": "你叫玛丽，是印刷厂里细心的女工。你善于倾听和调解，总是用温和的方式推动大家前进。你相信通过协商可以争取权益。",
    "杰克": "你叫杰克，是印刷厂的学徒，充满理想。你虽然年轻，但愿意学习，也愿意支持正确的行动。你说话真诚，容易感动。"
}

# 初始化 session state（保存游戏状态）
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
    st.session_state.logs = []   # 存储对话日志
    st.session_state.waiting_for_response = False   # 是否等待AI回复
    st.session_state.pending_action = None          # 待处理的玩家选择

MAX_DAYS = 7

def get_response(name, player_input=None):
    """与之前相同的 AI 调用逻辑"""
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

    # 状态更新（仅当玩家有输入时）
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
    """让三个 AI 依次说话"""
    for name in ["汤姆", "玛丽", "杰克"]:
        reply = get_response(name)
        st.session_state.logs.append(f"{name}: {reply}")
        st.session_state.messages.append({"role": "assistant", "name": name, "content": reply})
        time.sleep(0.3)   # 稍微延迟，模拟打字效果
    st.session_state.waiting_for_response = False

def player_choice(action):
    """处理玩家的选择"""
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

    # 让三个 AI 依次回应
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
        st.session_state.waiting_for_response = True

# ========== Streamlit 界面 ==========
st.set_page_config(page_title="1848 伦敦印刷厂", layout="centered")
st.title("📰 1848 伦敦印刷厂")
st.caption("你是一名新来的排字工，走进了工人们的休息室。")

# 显示角色状态卡片
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("汤姆", value=f"激进 {st.session_state.state['汤姆']['radical']}", delta=f"信任 {st.session_state.state['汤姆']['trust']}")
with col2:
    st.metric("玛丽", value=f"激进 {st.session_state.state['玛丽']['radical']}", delta=f"信任 {st.session_state.state['玛丽']['trust']}")
with col3:
    st.metric("杰克", value=f"激进 {st.session_state.state['杰克']['radical']}", delta=f"信任 {st.session_state.state['杰克']['trust']}")

# 显示对话记录
chat_container = st.container()
with chat_container:
    for log in st.session_state.logs[-30:]:  # 只显示最近30条
        if log.startswith("你:"):
            st.markdown(f"<div style='text-align: right; color: #1f77b4;'>{log}</div>", unsafe_allow_html=True)
        elif log.startswith("系统"):
            st.info(log)
        else:
            st.write(log)

# 游戏控制
if st.session_state.game_active:
    # 显示当前天数
    st.write(f"**第 {st.session_state.current_day} / {MAX_DAYS} 天**")

    # 等待AI对话或玩家选择
    if st.session_state.waiting_for_response:
        # 显示AI对话已完成，等待玩家选择
        st.write("工人们聊完了，你想说什么？")
        action = st.radio("你的态度：", ["支持罢工", "建议冷静", "表达担忧", "沉默不语"], index=None, horizontal=True)
        if action:
            # 根据选择映射到内部动作
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
        # 开始一轮AI对话（先显示加载状态）
        with st.spinner("工人们在交谈..."):
            run_ai_turn()
        st.rerun()
else:
    st.success("游戏结束！")
    st.write(st.session_state.logs[-1])  # 显示结局
    if st.button("重新开始"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# 在侧边栏显示图片（可选）
with st.sidebar:
    st.header("场景")
    # 加载背景图（如果存在）
    bg_path = os.path.join(BASE_DIR, "factory_bg.png")
    if os.path.exists(bg_path):
        try:
            img = Image.open(bg_path)
            st.image(img, use_container_width=True)
        except:
            pass
    # 加载头像缩略图
    for name in ["汤姆", "玛丽", "杰克"]:
        img_path = os.path.join(BASE_DIR, f"{name}.png")
        if os.path.exists(img_path):
            try:
                img = Image.open(img_path)
                st.image(img, width=60, caption=name)
            except:
                pass
