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

# log
log_file = os.getenv('LOG_FILE', 'app.log')
logging.basicConfig(filename=log_file, level=logging.INFO,
                    format='%(asctime)s:%(levelname)s:%(message)s')

api_key = os.getenv("GEMINI_KEY")
if api_key is None:
    logging.error("API key not found in environment variables.")
    raise ValueError("API key not found in environment variables")

# default role
default_role = ("""
Role: You are a knowledgeable travel guide and planner. 
Your task is to help clients plan their trips to any location worldwide. 
When engaging with clients, ask them for more details if the information they provide is insufficient for planning the itinerary. 
Gather essential details such as their travel dates, preferred destinations, interests (e.g., culture, adventure, relaxation), 
budget, and any special requests. Your responses should be friendly, informative, and proactive in guiding them through the planning process.
""")
default_model = "gemini-1.0-pro-latest"


def extract_text(response_data):
    """
    Extracts text content from the API response.
    """
    try:
        candidates = response_data.get('candidates', [])
        if not candidates:
            logging.warning("No candidates found in the response.")
            return "I'm sorry, but I couldn't generate a response at the moment."

        content = candidates[0].get('content', {})
        parts = content.get('parts', [])
        if not parts:
            logging.warning("No parts found in the content.")
            return "I'm having trouble finding the right words. Please try again."

        text = parts[0].get('text', "I'm not sure how to respond to that. Could you clarify?")
        return text
    except Exception as e:
        logging.error(f"Error extracting text: {str(e)}")
        return f"Something went wrong: {str(e)}"


def generate_prompt(user_input, role=default_role, history=None):
    """
    Generates the prompt to be sent to the API, including conversation history.
    """
    if history is None:
        history = []
    conversation_history = history + [f"User: {user_input}"]
    prompt = f"{role}\n" + "\n".join(conversation_history) + "\nAssistant:"
    logging.info(f"Generated prompt: {prompt}")
    return prompt, conversation_history


def call_google_api(prompt):
    """
    Calls the Google API with the generated prompt.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{default_model}:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        logging.info("API call successful.")
        return extract_text(response.json()), None
    except requests.exceptions.RequestException as e:
        logging.error(f"Request to Google API failed: {str(e)}")
        return "I'm sorry, I couldn't process your request at the moment. Please try again later.", str(e)


def process_chat(user_input, role=default_role, history=None):
    """
    Processes the chat by generating the prompt and calling the API.
    """
    prompt, conversation_history = generate_prompt(user_input, role, history)
    bot_reply, error = call_google_api(prompt)

    if error:
        logging.error(f"Error in processing chat: {error}")
        return bot_reply, conversation_history, error

    conversation_history.append(f"Assistant: {bot_reply}")
    logging.info(f"Assistant reply: {bot_reply}")
    return bot_reply, conversation_history, None


# Flask route to handle the chat requests
@app.route('/chat', methods=['POST'])
def chat():
    data = request.json

    # Extracting user input, role and history from request
    user_input = data.get('message', "")
    role = data.get('role', default_role)
    history = data.get('conversation_history', [])

    logging.info(f"Received user input: {user_input}")

    # Process chat
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