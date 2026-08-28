import asyncio
from app.providers.ollama import OllamaProvider
from app.providers.base import LLMMessage

async def main():
    provider = OllamaProvider()
    res = await provider.generate(
        messages=[LLMMessage(role="user", content="Who are you and who is Lenny?")],
        system="You are the Lenny Growth Assistant. You know that Lenny is the host of Lenny's Podcast.",
        max_tokens=100,
    )
    print("RESPONSE:", res.content)

asyncio.run(main())
