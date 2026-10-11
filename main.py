
import os
from dotenv import load_dotenv
import neatlogs
from openai import OpenAI

# Load keys from the .env file
load_dotenv()

# Connect to NeatLogs
neatlogs.init(
    api_key=os.environ["NEATLOGS_API_KEY"],
    workflow_name="my-first-app",
)

# Connect to OpenAI
client = neatlogs.wrap(OpenAI())

# Make a test AI request
try:
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "user", "content": "What is the capital of Spain?"}
        ],
    )
    print(response.choices[0].message.content)
finally:
    # Send traces even if the request failed
    neatlogs.flush()
    neatlogs.shutdown()
