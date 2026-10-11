import os
from dotenv import load_dotenv
import neatlogs
from google import genai

# Load keys from the .env file
load_dotenv()

# Connect to NeatLogs
neatlogs.init(
    api_key=os.environ["NEATLOGS_API_KEY"],
    workflow_name="my-first-app",
)

# Connect to Gemini (reads GEMINI_API_KEY from the environment)
client = neatlogs.wrap(genai.Client())

# Make a test AI request
try:
    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents="What is the capital of Spain?",
    )
    print(response.text)
finally:
    # Send traces even if the request failed
    neatlogs.flush()
    neatlogs.shutdown()
