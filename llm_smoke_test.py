
from dotenv import load_dotenv

load_dotenv()  # load both keys from .env

from langchain.chat_models import init_chat_model

model = init_chat_model("openai:gpt-5.4-mini")
reply = model.invoke("Reply with exactly: LLM is working")
print(reply.content)
