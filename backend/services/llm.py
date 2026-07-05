"""
services/llm.py
Single wrapper so the rest of the codebase (and Yusra's LangGraph nodes) never
call Gemini/OpenAI directly — just `ask_llm(prompt)` and `get_embedding(text)`.
Swapping providers only means changing LLM_PROVIDER in .env.

NOTE: as of mid-2026 Google replaced the old `google-generativeai` package
(and its AIza-style keys) with the new `google-genai` SDK, which is required
for the newer "auth key" (AQ.Ab...) format that Google AI Studio now issues
by default. If your Gemini calls fail with "API key not valid" using the old
package, this is why — make sure requirements.txt lists `google-genai`, not
`google-generativeai`.
"""
from config import settings

_gemini_client = None
_openai_client = None


def _get_gemini_client():
    global _gemini_client
    if _gemini_client is None:
        from google import genai
        _gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _gemini_client


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
    from google.genai import types

    client = _get_gemini_client()
    config = types.GenerateContentConfig(system_instruction=system) if system else None
    resp = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=config,
    )
    return resp.text


def get_embedding(text: str) -> list[float]:
    """
    Returns a vector embedding for `text`, using whichever provider is
    configured in .env (LLM_PROVIDER). Used by services/rag.py to index
    and search the loan policy document.
    """
    text = text.replace("\n", " ").strip()

    if settings.LLM_PROVIDER == "openai":
        client = _get_openai_client()
        resp = client.embeddings.create(model="text-embedding-3-small", input=text)
        return resp.data[0].embedding

    # default: gemini
    client = _get_gemini_client()
    resp = client.models.embed_content(model="gemini-embedding-001", contents=text)
    return resp.embeddings[0].values
