import requests
import streamlit as st
import sys
import os
from revChatGPT.V3 import Chatbot

os.environ["API_URL"] = "https://chimeragpt.adventblocks.cc/api/v1/chat/completions"

st.set_page_config(page_title="ChimeraGPT", page_icon='random', layout="wide")
st.title('ChimeraGPT')
with st.sidebar:
    
    model = st.selectbox("选择模型:", ["gpt-4", "gpt-3.5-turbo",
                                       "gpt-3.5-turbo-16k",
                                       "gpt-3.5-turbo-0301",
                                       "gpt-3.5-turbo-0613",
                                       "gpt-3.5-turbo-16k-0613"])
    key = st.text_input("KEY:")
    if model and key:
        system_prompt = f'You are ChatGPT,  a large language model({model}) trained by OpenAI. Respond conversationally'
        system_prompt = st.text_area("设定", system_prompt)
        if 'system_prompt' not in st.session_state:
            st.session_state.system_prompt = system_prompt
        else:
            if st.session_state.system_prompt != system_prompt:
                st.session_state.system_prompt = system_prompt
                st.session_state.bot.reset(system_prompt=system_prompt)
                st.session_state.messages = st.session_state.bot.conversation["default"]
        if 'model' in st.session_state:
            if model != st.session_state.model:
                st.session_state.model = model
                st.session_state.bot = Chatbot(engine=st.session_state.model,
                                               proxy=st.secrets["proxy"],
                                               system_prompt=system_prompt, api_key=st.secrets["api_key"])

        else:
            st.session_state.model = model
            st.session_state.bot = Chatbot(engine=model,
                                           proxy=st.secrets["proxy"],
                                           system_prompt=system_prompt, api_key=st.secrets["api_key"])
            st.session_state.messages = st.session_state.bot.conversation["default"]

# Accept user input
if key:
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = st.session_state.bot.conversation["default"]

    # Display chat messages from history on app rerun
    for message in st.session_state.messages:
        with st.chat_message(message["role"].replace("system", "user")):
            st.markdown(message["content"])
        prompt = st.chat_input("输入你的困惑")
        if prompt:
            # Add user message to chat history
            st.session_state.messages.append({"role": "user", "content": prompt})
            # Display user message in chat message container
            with st.chat_message("user"):
                st.markdown(prompt)
            # Display assistant response in chat message container
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                prompt = prompt.strip()
                full_response = ""
                if prompt.startswith("/"):
                    order = prompt.split(" ", 1)[0]
                    if order == "/reset":
                        st.session_state.bot.reset()
                        st.session_state.messages = st.session_state.bot.conversation["default"]
                        message_placeholder.button("重置成功!")
                    elif order == "/draw":
                        message = prompt.split(" ", 1)[1]
                        message_placeholder.markdown(full_response + "▌")
                        image_url = st.session_state.bot.image_create(message, size="800x800")[0]
                        full_response = f"""![pic]({image_url})"""
                        message_placeholder.markdown(full_response)
                    elif order == "/draws":
                        message = prompt.split(" ", 1)[1]
                        message_placeholder.markdown(full_response + "▌")
                        image_urls = st.session_state.bot.image_create(message.rsplit(" ", 1)[-1], n=message.split(" ", 1)[0])
                        for image_url in image_urls:
                            full_response += f"""![pic]({image_url})\n"""
                        message_placeholder.markdown(full_response)
                    else:
                        message_placeholder.markdown("未知指令!")
                else:
                    print('收到消息:', prompt, '\n等待响应:')
                    for chunk in st.session_state.bot.ask_stream(prompt):
                        if chunk:
                            full_response += chunk + ""
                            message_placeholder.markdown(full_response + "▌")
                    message_placeholder.markdown(full_response)
            # Add assistant response to chat history
            st.session_state.messages.append({"role": "assistant", "content": full_response})
else:
    st.warning("NEED KEY")
