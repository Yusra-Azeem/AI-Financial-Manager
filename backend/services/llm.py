"""
services/llm.py
Single wrapper so the rest of the codebase (and Yusra's LangGraph nodes) never
call Gemini/OpenAI directly — just `ask_llm(prompt)`. Swapping providers only
means changing LLM_PROVIDER in .env.
"""
from config import settings

_gemini_model = None
_openai_client = None


def _get_gemini_model():
    global _gemini_model
    if _gemini_model is None:
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        _gemini_model = genai.GenerativeModel("gemini-1.5-flash")
    return _gemini_model


def _get_openai_client():
    global _openai_client
    if _openai_client is None:
        from openai import OpenAI
        _openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _openai_client


def ask_llm(prompt: str, system: str = "") -> str:
    """
    Sends a prompt to whichever provider is configured in .env (LLM_PROVIDER).
    Returns plain text. Keep prompts asking for JSON explicit about "return ONLY JSON".
    """
    full_prompt = f"{system}\n\n{prompt}" if system else prompt

    if settings.LLM_PROVIDER == "openai":
        client = _get_openai_client()
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
        )
        return resp.choices[0].message.content

    # default: gemini
    model = _get_gemini_model()
    resp = model.generate_content(full_prompt)
    return resp.text
