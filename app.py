import os
import openai
import requests
import json
import streamlit as st
from openai import OpenAI
import time

# --- ページ設定 ---
st.set_page_config(page_title="Multi-Room Chat", layout="wide")

# --- CSSスタイル ---
# (元のコードから変更なし)
st.markdown(
    """
    <style>
        body { background-color: #f0f0f0; }
        .main { background-color: #f0f0f0; }
        .chat-container {
            max-width: 750px;
            margin: auto;
            background-color: white;
            border-radius: 8px;
            padding: 20px 20px 100px 20px;
            min-height: 90vh; /* 少し高さを調整 */
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }
        .stChatMessage { padding: 0 !important; }
        .user-bubble {
            background-color: #0b93f6; color: white; padding: 10px 14px;
            border-radius: 18px; margin: 5px 0; max-width: 75%;
            margin-left: auto; text-align: left;
        }
        .assistant-bubble {
            background-color: #e5e5ea; color: black; padding: 10px 14px;
            border-radius: 18px; margin: 5px 0; max-width: 75%;
            margin-right: auto; text-align: left;
        }
        .stTextInput > div > div > input {
            border-radius: 18px; padding: 10px 14px;
            border: 1px solid #ccc; width: 100%;
        }
        /* サイドバーのアクティブなボタンを目立たせる */
        .st-emotion-cache-12w0qpk button {
            background-color: #e5e5ea;
        }
        footer {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True
)


# --- APIクライアントの初期化 ---
try:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    notion_api_key = st.secrets["NOTION_API_KEY"]
    notion_database_id = st.secrets["NOTION_DATABASE_ID"]
except (FileNotFoundError, KeyError):
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    notion_api_key = os.getenv("NOTION_API_KEY")
    notion_database_id = os.getenv("NOTION_DATABASE_ID")

# --- Notion保存機能 ---
# (元のコードから変更なし)
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
        return True, "✅ Notionに保存しました。"
    except requests.exceptions.RequestException as e:
        st.error(f"Notion API Error: {e}")
        return False, f"❌ Notion保存エラー: {e}"

# --- チャット管理関数 ---
def create_new_chat():
    """新しいチャットセッションを作成する"""
    chat_id = f"chat_{int(time.time())}"
    st.session_state.chat_history[chat_id] = []
    st.session_state.active_chat_id = chat_id
    
# --- セッションステートの初期化 ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = {}
if "active_chat_id" not in st.session_state:
    st.session_state.active_chat_id = None

# 初回起動時にデフォルトのチャットルームを作成
if not st.session_state.chat_history:
    create_new_chat()

# --- サイドバーUI ---
with st.sidebar:
    st.title("チャットルーム")
    if st.button("➕ 新しいチャット", use_container_width=True):
        create_new_chat()
        st.rerun()

    st.markdown("---")
    
    # 新しいチャットが上にくるように履歴をソート
    chat_ids = sorted(st.session_state.chat_history.keys(), reverse=True)
    
    for chat_id in chat_ids:
        history = st.session_state.chat_history[chat_id]
        # チャットの最初のユーザーメッセージをタイトルにする
        title = "新しいチャット"
        for msg in history:
            if msg["role"] == "user":
                title = msg["content"][:25] + "..." if len(msg["content"]) > 25 else msg["content"]
                break
        
        # 現在アクティブなチャットルームのボタンの種類を変更して目立たせる
        button_type = "primary" if chat_id == st.session_state.active_chat_id else "secondary"
        if st.button(title, key=chat_id, use_container_width=True, type=button_type):
            st.session_state.active_chat_id = chat_id
            st.rerun()

# --- メインのチャット画面 ---
st.markdown('<div class="chat-container">', unsafe_allow_html=True)
st.markdown("<h2 style='text-align:center; margin-bottom:20px;'>ChatGPT Clone</h2>", unsafe_allow_html=True)

# アクティブなチャットの履歴を表示
active_chat_messages = st.session_state.chat_history.get(st.session_state.active_chat_id, [])
for message in active_chat_messages:
    bubble_class = "user-bubble" if message["role"] == "user" else "assistant-bubble"
    st.markdown(f"<div class='{bubble_class}'>{message['content']}</div>", unsafe_allow_html=True)

# チャット入力欄
if prompt := st.chat_input("メッセージを入力してください"):
    # 現在のチャット履歴にユーザーのメッセージを追加
    st.session_state.chat_history[st.session_state.active_chat_id].append({"role": "user", "content": prompt})
    
    # APIに渡すメッセージリスト（現在のチャットルームの全履歴）
    messages_for_api = st.session_state.chat_history[st.session_state.active_chat_id]

    try:
        # --- OpenAI API呼び出し ---
        # ※注意: "gpt-5-nano"は存在しないモデルです。実際のモデル名に変更してください。
        completion = client.chat.completions.create(
            model="gpt-4-turbo",  # または "gpt-3.5-turbo" など
            messages=messages_for_api,
        )
        ai_response = completion.choices[0].message.content

        # AIの応答を履歴に追加
        st.session_state.chat_history[st.session_state.active_chat_id].append({"role": "assistant", "content": ai_response})
        
        # Notionに保存
        if notion_api_key and notion_database_id:
            save_to_notion(prompt, ai_response)

        # 画面を再描画してチャットを更新
        st.rerun()

    except Exception as e:
        st.error(f"API呼び出し中にエラーが発生しました: {e}")

st.markdown('</div>', unsafe_allow_html=True)
