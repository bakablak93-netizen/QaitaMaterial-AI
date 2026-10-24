from app.core.config import settings

def configured():
    s=settings()
    return bool(s.ai_enabled and s.llm_api_key and s.llm_api_key != "PASTE_YOUR_AI_API_KEY_HERE")

async def chat(messages, language="ru"):
    if not configured(): return None
    from openai import AsyncOpenAI
    s=settings()
    kwargs={"api_key":s.llm_api_key,"timeout":25.0,"max_retries":1}
    if s.llm_base_url: kwargs["base_url"]=s.llm_base_url
    client=AsyncOpenAI(**kwargs)
    system=("You are Qaita AI Assistant. Reply in the user's requested language: "+language+
      ". You may answer general questions. For industrial material safety never claim certification, "
      "regulatory compliance or laboratory test results. State uncertainty. No database access is granted.")
    response=await client.chat.completions.create(model=s.llm_model,messages=[{"role":"system","content":system}]+messages,max_tokens=600)
    return response.choices[0].message.content or ""
