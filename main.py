#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# @Project ：pythonProject 
# @File    ：main.py
# @Author  ：Swift
# @Date    ：2024/9/29 15:45

import logging
import os
import requests
import json
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

app = Flask(__name__)

# 日志配置
log_file = os.getenv('LOG_FILE', 'app.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s:%(levelname)s:%(message)s',
    handlers=[
        logging.FileHandler(log_file),  # 写入日志文件
        logging.StreamHandler()  # 输出到标准输出
    ]
)

# 获取 API keys
gemini_key = os.getenv("GEMINI_KEY")
yi_key = os.getenv("YI_KEY")

# 检查 API keys
if not gemini_key:
    logging.error("GEMINI_KEY not found in environment variables.")
if not yi_key:
    logging.error("YI_KEY not found in environment variables.")
if not gemini_key or not yi_key:
    raise ValueError("Missing one or both API keys. Check environment variables.")

# 默认角色和模型
default_role = """
Role: You are a knowledgeable travel guide and planner. 
Your task is to help clients plan their trips to any location worldwide. 
When engaging with clients, ask them for more details if the information they provide is insufficient for planning the itinerary. 
Gather essential details such as their travel dates, preferred destinations, interests (e.g., culture, adventure, relaxation), 
budget, and any special requests. Your responses should be friendly, informative, and proactive in guiding them through the planning process.
"""
default_model = "gemini-1.0-pro-latest"


def extract_text(response_data):
    """
    提取 API 响应中的文本，兼容 'candidates' 和 'choices' 格式。
    """
    try:
        candidates = response_data.get('candidates', [])
        if candidates:
            content = candidates[0].get('content', {})
            parts = content.get('parts', [])
            if parts:
                text = parts[0].get('text', "I'm not sure how to respond to that. Could you clarify?")
                return text
            logging.warning("No parts found in the content (candidates).")
            return "I'm having trouble finding the right words. Please try again."

        choices = response_data.get('choices', [])
        if choices:
            message = choices[0].get('message', {})
            text = message.get('content', "I'm not sure how to respond to that. Could you clarify?")
            return text
        logging.warning("No choices found in the response.")
        return "I'm sorry, but I couldn't generate a response at the moment."

    except Exception as e:
        logging.error(f"Error extracting text: {str(e)}")
        return f"Something went wrong: {str(e)}"


def generate_prompt(user_input, role=default_role, history=None):
    """
    生成发送到 API 的提示，包括对话历史。
    """
    if history is None:
        history = []
    conversation_history = history + [f"User: {user_input}"]
    prompt = f"{role}\n" + "\n".join(conversation_history) + "\nAssistant:"
    logging.info(f"Generated prompt: {prompt}")
    return prompt, conversation_history


def call_google_api(prompt):
    """
    调用 Google API 发送生成的提示。
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{default_model}:generateContent?key={gemini_key}"
    headers = {'Content-Type': 'application/json'}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()  # 如果响应状态码不是 200，则抛出异常
        logging.info("Google API call successful.")
        return extract_text(response.json()), None
    except requests.exceptions.RequestException as e:
        logging.error(f"Request to Google API failed: {str(e)}")
        return "I'm sorry, I couldn't process your request at the moment. Please try again later.", str(e)


def call_Yi_api(prompt):
    """
    调用零一万物 API 发送生成的提示。
    """
    url = "https://api.lingyiwanwu.com/v1/chat/completions"
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {yi_key}'  # 从环境变量中获取 YI_KEY
    }
    payload = {
        "model": "yi-large",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()  # 如果响应状态码不是 200，则抛出异常
        logging.info("Lingyiwanwu API call successful.")
        return extract_text(response.json()), None
    except requests.exceptions.RequestException as e:
        logging.error(f"Request to Lingyiwanwu API failed: {str(e)}")
        return "I'm sorry, I couldn't process your request at the moment. Please try again later.", str(e)


def process_chat(user_input, role=default_role, history=None):
    """
    处理聊天请求：生成提示并调用 API。
    """
    prompt, conversation_history = generate_prompt(user_input, role, history)

    # 这里可以灵活选择调用 Google API 或 Lingyiwanwu API
    # bot_reply, error = call_google_api(prompt)
    bot_reply, error = call_Yi_api(prompt)

    if error:
        logging.error(f"Error in processing chat: {error}")
        return bot_reply, conversation_history, error

    conversation_history.append(f"Assistant: {bot_reply}")
    logging.info(f"Assistant reply: {bot_reply}")
    return bot_reply, conversation_history, None


@app.route('/chat', methods=['POST'])
def chat():
    data = request.json

    # 从请求中提取用户输入、角色和历史记录
    user_input = data.get('message', "")
    role = data.get('role', default_role)
    history = data.get('conversation_history', [])

    logging.info(f"Received user input: {user_input}")

    # 处理聊天请求
    bot_reply, updated_history, error = process_chat(user_input, role, history)

    if error:
        return jsonify({"error": error, "message": bot_reply}), 500

    return jsonify({
        "reply": bot_reply,
        "conversation_history": updated_history
    }), 200


@app.route('/')
def home():
    logging.info("Home route accessed.")
    return "Welcome to my Flask App!"


if __name__ == '__main__':
    logging.info("Starting Flask application...")
    app.run(host='0.0.0.0', port=8080)