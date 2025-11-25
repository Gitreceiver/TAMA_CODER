from openai import AsyncOpenAI
from config import settings # Import the actual settings

# Initialize the AsyncOpenAI client
client = AsyncOpenAI(
    api_key=settings.DEEPSEEK_API_KEY,  # Use DeepSeek API key from settings
    base_url=settings.DEEPSEEK_BASE_URL # Use DeepSeek base URL from settings
)

# You can add wrapper functions here if needed, e.g.,
# async def generate_response(messages: list, tools: list):
#     response = await client.chat.completions.create(
#         model=settings.DEFAULT_AI_MODEL,
#         messages=messages,
#         tools=tools,
#         stream=False
#     )
#     return response
