from dotenv import load_dotenv

load_dotenv()  # copy .env values into this program's environment

from langsmith import traceable


@traceable(name="smoke-test")
def greet(name: str) -> str:
    return f"Hello, {name}!"


print(greet("LangSmith"))
