import os
import openai
import requests
import json
import streamlit as st
from openai import OpenAI

# --- ページ設定 ---
st.set_page_config(page_title="ChatGPT", layout="wide")
st.markdown(
    """
    <style>
        body {
            background-color: #f0f0f0;
        }
        .main {
            background-color: #f0f0f0;
        }
        .chat-container {
            max-width: 750px;
            margin: auto;
            background-color: white;
            border-radius: 8px;
            padding: 20px 20px 100px 20px;
            min-height: 100vh;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }
        .stChatMessage {
            padding: 0 !important;
        }
        .user-bubble {
            background-color: #0b93f6;
            color: white;
            padding: 10px 14px;
            border-radius: 18px;
            margin: 5px 0;
            max-width: 75%;
            margin-left: auto;
            text-align: left;
        }
        .assistant-bubble {
            background-color: #e5e5ea;
            color: black;
            padding: 10px 14px;
            border-radius: 18px;
            margin: 5px 0;
            max-width: 75%;
            margin-right: auto;
            text-align: left;
        }
        .stTextInput > div > div > input {
            border-radius: 18px;
            padding: 10px 14px;
            border: 1px solid #ccc;
            width: 100%;
        }
        footer {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown('<div class="chat-container">', unsafe_allow_html=True)
st.markdown("<h2 style='text-align:center; margin-bottom:20px;'>ChatGPT</h2>", unsafe_allow_html=True)

# --- クライアントの初期化 ---
try:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    notion_api_key = st.secrets["NOTION_API_KEY"]
    notion_database_id = st.secrets["NOTION_DATABASE_ID"]
except FileNotFoundError:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    notion_api_key = os.getenv("NOTION_API_KEY")
    notion_database_id = os.getenv("NOTION_DATABASE_ID")

# --- Notion保存 ---
def save_to_notion(prompt, response):
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {notion_api_key}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }
    new_page_data = {
        "parent": {"database_id": notion_database_id},
        "properties": {
            "Prompt": {"title": [{"text": {"content": prompt}}]},
            "Response": {"rich_text": [{"text": {"content": response}}]},
        },
    }
    try:
        res = requests.post(url, headers=headers, data=json.dumps(new_page_data))
        res.raise_for_status()
        return True, "Notionに保存しました。"
    except requests.exceptions.RequestException as e:
        return False, f"Notion保存エラー: {e}"

# --- チャット履歴 ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 表示 ---
for message in st.session_state.messages:
    if message["role"] == "user":
        st.markdown(f"<div class='user-bubble'>{message['content']}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='assistant-bubble'>{message['content']}</div>", unsafe_allow_html=True)

# --- 入力 ---
if prompt := st.chat_input("メッセージを入力してください"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.markdown(f"<div class='user-bubble'>{prompt}</div>", unsafe_allow_html=True)

    completion = client.chat.completions.create(
        model="gpt-5-nano",
        messages=[
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.messages
        ],
    )
    ai_response = completion.choices[0].message.content
    st.session_state.messages.append({"role": "assistant", "content": ai_response})
    st.markdown(f"<div class='assistant-bubble'>{ai_response}</div>", unsafe_allow_html=True)

    success, message = save_to_notion(prompt, ai_response)
    if success:
        st.toast(message)
    else:
        st.toast(message)

st.markdown('</div>', unsafe_allow_html=True)
