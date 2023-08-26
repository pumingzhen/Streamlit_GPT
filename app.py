import json
import sys
import time
import requests
import streamlit as st
from streamlit_javascript import st_javascript
import gpt_api

st.set_page_config(page_title="ChatGPT", page_icon='🤖', layout="wide")


def get_from_local_storage(k, out=[]):
    if k not in st.session_state:
        with st.spinner(f"Load {k}"):
            v = st_javascript(f"JSON.parse(localStorage.getItem('{k}'));")
            time.sleep(0.5)
        return v or out
    else:
        return st.session_state[k]


def set_to_local_storage(k, v):
    jdata = json.dumps(v)
    st_javascript(
        f"localStorage.setItem('{k}', JSON.stringify({jdata}));")


def get_con_title():
    # return "test"
    bot_ = gpt_api.Chatbot(engine="gpt-3.5-turbo", temperature=0, url_base=st.session_state['base_url']+ "/chat/completions")
    bot_.conversation['default'] = st.session_state.messages['default'].copy()
    chat_title = bot_.ask("总结上述对话, 10字以内", model="gpt-3.5-turbo")
    return chat_title


def save_to_local_storage(model_name):
    with st.spinner("正在保存当前会话"):
        title = get_con_title()
        _con_dict = {"title": title, "conversation": st.session_state.messages}
        st.session_state[f"{model_name}_con"].insert(0, _con_dict)
        set_to_local_storage(f"{model_name}_con", st.session_state[f"{model_name}_con"])
        st.success(f"{title} 保存成功!")


def set_chat(model_name):
    save_to_local_storage(model_name)
    st.session_state[f"{model_name}_con"] = get_from_local_storage(f"{model_name}_con")


def save_key(k):
    st.session_state['url_key'].update({k: st.session_state[k]})
    set_to_local_storage('url_key', st.session_state['url_key'])


if 'url_key' not in st.session_state:
    st.session_state['url_key'] = get_from_local_storage("url_key", out={})


with st.sidebar:
    base_url = st.text_input("Base URL:", st.session_state['url_key'].get("base_url") or "", on_change=save_key, args=('base_url',), key="base_url", type="password")
    key = st.text_input("Key:", st.session_state['url_key'].get("key") or "", on_change=save_key, key="key", args=('key',), type="password")
    if not (base_url and key):
        st.warning("请输入Base URL和Key")
        st.stop()

    if 'models' not in st.session_state:
        with st.spinner("加载模型中..."):
            response = requests.get(f"{base_url}/api/v1/models").json()['data']
            st.session_state.models = [i['id'] for i in response]
            st.session_state.tokens_dict = {i["id"]: i.get('tokens') for i in response}

    model = st.selectbox("选择模型:", st.session_state.models)
    system_prompt = f'You are {model}, a large language model. Respond conversationally and use markdown formatting.'
    system_prompt = st.text_area("设定", system_prompt)
    if ("my_system_prompt" not in st.session_state) or (st.session_state.get("my_system_prompt") != system_prompt):
        st.session_state.my_system_prompt = system_prompt
        st.session_state.messages = {"default": [{"role": "system", "content": system_prompt}]}
    # st.write("--------------------------------------------")
    col1, col2 = st.columns(2)

    if col1.button("New Chat", use_container_width=True):
        st.session_state.messages = {"default": [{"role": "system", "content": system_prompt}]}
    if col2.button("Retry", use_container_width=True):
        if st.session_state.messages['default'][-1]['role'] == 'user':
            st.session_state.messages['default'].pop()
        else:
            st.session_state.messages['default'].pop()
            st.session_state.messages['default'].pop()
        retry_prompt = st.session_state.last_prompt
    else:
        retry_prompt = None
    st.write("--------------------------------------------")

    st.session_state[f"{model}_con"] = get_from_local_storage(f"{model}_con")
    con_dict = st.selectbox("选择会话:", st.session_state[f"{model}_con"], format_func=lambda x: x.get("title"))
    col11, col22 = st.columns(2)
    if col11.button("Load", use_container_width=True):
        st.session_state.messages = con_dict["conversation"]
    col22_b = col22.button("Save", on_click=set_chat, args=(model,), use_container_width=True)
    if base_url.endswith(".php"):
        response = requests.get(st.secrets['chat_count_url'])
        st.write(response.text)
    bot = gpt_api.Chatbot(engine=model, system_prompt=system_prompt, url_base=base_url + "/api/v1/chat/completions", api_key=key)
    bot.conversation = st.session_state.messages

st.title('ChatGPT')


for message in st.session_state.messages["default"]:
    with st.chat_message(message["role"].replace("system", "user")):
        st.markdown(message["content"])

# Accept user input
prompt = st.chat_input("输入你的困惑") or retry_prompt
if prompt:
    # Display user message in chat message container
    with st.chat_message("user"):
        st.session_state.last_prompt = prompt
        st.markdown(prompt)
    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        with st.spinner("Thinking"):
            message_placeholder = st.empty()
            prompt = prompt.strip()
            full_response = ""
            if prompt.startswith("/"):
                order = prompt.split(" ", 1)[0]
                if order == "/retry":
                    prompt = bot.conversation['default'][-1]['content']
                    bot.rollback(1)
                    for chunk in bot.ask_stream(prompt):
                        if chunk:
                            full_response += chunk + ""
                            message_placeholder.markdown(full_response + "▌")
                    message_placeholder.markdown(full_response)
                else:
                    message_placeholder.markdown("未知指令!")
            else:
                for chunk in bot.ask_stream(prompt):
                    # print(chunk, end="")
                    if chunk:
                        full_response += chunk + ""
                        message_placeholder.markdown(full_response + "▌")

            message_placeholder.markdown(full_response)
