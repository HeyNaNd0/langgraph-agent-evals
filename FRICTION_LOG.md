# Friction log

What confused me while learning LangGraph + LangSmith from zero, logged as it happened.

| # | Area | What I was doing | Expected | Actual | Time lost | Suggested fix |
|---|------|------------------|----------|--------|-----------|---------------|
| 1 | Getting-started docs: OpenAI key prerequisite | Getting an OpenAI API key for my first LLM call | My ChatGPT subscription would cover the API calls | API usage is billed separately ([OpenAI help](https://help.openai.com/en/articles/9039756-managing-billing-for-chatgpt-and-the-api-platform)), so I had to add $10 of credit first. Afterward I checked the [Tracing quickstart](https://docs.langchain.com/langsmith/observability-quickstart): its prerequisites list "An OpenAI API key" with no note about cost. | __ min | Add one line under that prerequisite: "OpenAI API usage is billed separately from ChatGPT plans; add API credit before you start." |