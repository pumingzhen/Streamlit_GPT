import json
import os
import httpx
import openai
import requests
import tiktoken


def get_filtered_keys_from_object(obj: object, *keys: str):
    """
    Get filtered list of object variable names.
    :param keys: List of keys to include. If the first key is "not", the remaining keys will be removed from the class keys.
    :return: List of class keys.
    """
    class_keys = obj.__dict__.keys()
    if not keys:
        return set(class_keys)

    # Remove the passed keys from the class keys.
    if keys[0] == "not":
        return {key for key in class_keys if key not in keys[1:]}
    # Check if all passed keys are valid
    if invalid_keys := set(keys) - class_keys:
        raise ValueError(
            f"Invalid keys: {invalid_keys}",
        )
    # Only return specified keys that are in class_keys
    return {key for key in keys if key in class_keys}


class Chatbot:
    """
    Official ChatGPT API
    """

    def __init__(
            self,
            api_key: str = None,
            engine: str = "gpt-3.5.turbo",
            proxy: str = None,
            timeout: float = None,
            max_tokens: int = None,
            temperature: float = 0.5,
            top_p: float = 1.0,
            presence_penalty: float = 0.0,
            frequency_penalty: float = 0.0,
            reply_count: int = 1,
            truncate_limit: int = None,
            system_prompt: str = "You are ChatGPT, a large language model trained by OpenAI. Respond conversationally and use markdown formatting.",
            my_system_prompt: dict = None,
            url_base: str = None
    ) -> None:
        """
        Initialize Chatbot with API key (from https://platform.openai.com/account/api-keys)
        """
        if my_system_prompt is None:
            my_system_prompt = {"test": "You are ChatGPT, a large language model trained by Open"}
        self.my_system_prompt = my_system_prompt
        self.engine: str = engine
        self.api_key: str = api_key
        self.system_prompt: str = system_prompt
        self.url_base: str = url_base
        self.max_tokens: int = max_tokens or (
            31000
            if "gpt-4-32k" in engine
            else 7000
            if "gpt-4" in engine
            else 15000
            if "gpt-3.5-turbo-16k" in engine
            else 4000
        )
        self.truncate_limit: int = truncate_limit or (
            30500
            if "gpt-4-32k" in engine
            else 6500
            if "gpt-4" in engine
            else 14500
            if "gpt-3.5-turbo-16k" in engine
            else 3500
        )
        self.temperature: float = temperature
        self.top_p: float = top_p
        self.presence_penalty: float = presence_penalty
        self.frequency_penalty: float = frequency_penalty
        self.reply_count: int = reply_count
        self.timeout: float = timeout
        self.session = requests.Session()
        self.conversation: dict[str, list[dict]] = {
            "default": [
                {
                    "role": "system",
                    "content": system_prompt,
                },
            ],
        }
        try:
            system_prompt_len = self.get_token_count("default")
        except:
            system_prompt_len = len(self.system_prompt)
        if system_prompt_len > self.max_tokens:
            raise Exception("System prompt is too long")

    def add_to_conversation(
            self,
            message: str,
            role: str,
            convo_id: str = "default",
    ) -> None:
        """
        Add a message to the conversation
        """
        self.conversation[convo_id].append({"role": role, "content": message})

    def __truncate_conversation(self, convo_id: str = "default") -> None:
        """
        Truncate the conversation
        """
        while True:
            if (
                    self.get_token_count(convo_id) > self.truncate_limit
                    and len(self.conversation[convo_id]) > 1
            ):
                # Don't remove the first message
                self.conversation[convo_id].pop(1)
            else:
                break

    # https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb
    def get_token_count(self, convo_id: str = "default") -> int:
        """
        Get token count
        """
        if 'gpt' not in self.engine:
            tiktoken.model.MODEL_TO_ENCODING[self.engine] = "cl100k_base"

        tiktoken.model.MODEL_TO_ENCODING["gpt-4"] = "cl100k_base"

        encoding = tiktoken.encoding_for_model(self.engine)

        num_tokens = 0
        for message in self.conversation[convo_id]:
            # every message follows <im_start>{role/name}\n{content}<im_end>\n
            num_tokens += 5
            for key, value in message.items():
                if value:
                    num_tokens += len(encoding.encode(value))
                if key == "name":  # if there's a name, the role is omitted
                    num_tokens += 5  # role is always required and always 1 token
        num_tokens += 5  # every reply is primed with <im_start>assistant
        return num_tokens

    def get_max_tokens(self, convo_id: str) -> int:
        """
        Get max tokens
        """
        return self.max_tokens - self.get_token_count(convo_id)

    def ask_stream(
            self,
            prompt: str,
            role: str = "user",
            convo_id: str = "default",
            model: str = None,
            pass_history: bool = True,
            url_base = None,
            **kwargs,
    ):
        """
        Ask a question
        """
        # Make conversation if it doesn't exist
        if convo_id not in self.conversation:
            self.reset(convo_id=convo_id, system_prompt=self.system_prompt)
        self.add_to_conversation(prompt, "user", convo_id=convo_id)
        self.__truncate_conversation(convo_id=convo_id)
        # Get response
        url = url_base or self.url_base
        headers = {"Authorization": f"Bearer {kwargs.get('api_key', self.api_key)}"}
        response = self.session.post(
            url,
            headers=headers,
            json={
                "model": os.environ.get("MODEL_NAME") or model or self.engine,
                "messages": self.conversation[convo_id] if pass_history else [prompt],
                "stream": True,
                # kwargs
                "temperature": kwargs.get("temperature", self.temperature),
                "top_p": kwargs.get("top_p", self.top_p),
                "presence_penalty": kwargs.get(
                    "presence_penalty",
                    self.presence_penalty,
                ),
                "frequency_penalty": kwargs.get(
                    "frequency_penalty",
                    self.frequency_penalty,
                ),
                "n": kwargs.get("n", self.reply_count),
                "user": role,
                "max_tokens": min(
                    self.get_max_tokens(convo_id=convo_id),
                    kwargs.get("max_tokens", self.max_tokens),
                ),
            },
            timeout=kwargs.get("timeout", self.timeout),
            stream=True,
        )
        if response.status_code != 200:
            raise Exception(
                f"{response.status_code} {response.reason} {response.text}",
            )
        response_role: str or None = None
        full_response: str = ""
        for line in response.iter_lines():
            if not line:
                continue
            # Remove "data: "
            line = line.decode("utf-8")[6:]
            if line == "[DONE]":
                break
            resp: dict = json.loads(line)
            choices = resp.get("choices")
            if not choices:
                continue
            delta = choices[0].get("delta")
            if not delta:
                continue
            if "role" in delta:
                response_role = delta["role"]
            if "content" in delta:
                content = delta["content"]
                full_response += content
                yield content
        self.add_to_conversation(full_response, response_role, convo_id=convo_id)

    def ask(
            self,
            prompt: str,
            role: str = "user",
            convo_id: str = "default",
            model: str = None,
            pass_history: bool = True,
            **kwargs,
    ) -> str:
        """
        Non-streaming ask
        """
        response = self.ask_stream(
            prompt=prompt,
            role=role,
            convo_id=convo_id,
            model=model,
            pass_history=pass_history,
            **kwargs,
        )
        full_response: str = "".join(response)
        return full_response

    def rollback(self, n: int = 1, convo_id: str = "default") -> None:
        """
        Rollback the conversation
        """
        for _ in range(n):
            self.conversation[convo_id].pop()

    def reset(self, convo_id: str = "default", system_prompt: str = None) -> None:
        """
        Reset the conversation
        """
        self.conversation[convo_id] = [
            {"role": "system", "content": system_prompt or self.system_prompt},
        ]

    def image_create(self, prompt, n=1, size="1024x1024"):
        print(n, size)
        response = openai.Image.create(prompt=prompt, n=n, size=size)
        print(response["data"])
        return [v['url'] for v in response['data']]


if __name__ == '__main__':
    bot = Chatbot()
    for query in bot.ask_stream('晚来天欲雪，能饮一杯无，什么意思', convo_id='test'):
        print(query, end="", flush=True)
