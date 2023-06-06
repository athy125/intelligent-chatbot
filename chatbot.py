from fastapi import FastAPI, HTTPException
from slack_sdk import WebClient
from slack_sdk.signature import SignatureVerifier
from dotenv import load_dotenv
import os
import openai

# Load environment variables
load_dotenv()

# Initialize FastAPI app and Slack client
app = FastAPI()
slack_client = WebClient(token=os.environ.get('SLACK_TOKEN'))

# Initialize OpenAI
openai.api_key = os.environ.get('OPENAI_API_KEY')

# Create a signature verifier for Slack events
signature_verifier = SignatureVerifier(os.environ.get('SLACK_SIGNING_SECRET'))

# Create a logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger.addHandler(handler)


# Route for Slack event subscription
@app.post('/slack/events')
async def slack_events(request):
    # Verify the incoming request signature
    if not signature_verifier.is_valid_request(request.body, request.headers):
        raise HTTPException(status_code=400, detail='Invalid request')

    # Parse the event data from the request
    data = await request.json()
    event = data['event']
    event_type = event['type']
    event_text = event.get('text')

    # Process the event based on its type
    if event_type == 'message' and event_text:
        response_text = await process_message(event_text)
        await send_message(event['channel'], response_text)

    return {'success': True}


# Process the incoming message using OpenAI
async def process_message(message):
    # Use OpenAI to generate a response
    prompt = f"User: {message}\nBot:"
    try:
        response = await asyncio.create_task(openai.Completion.create(
            engine='text-davinci-003',
            prompt=prompt,
            temperature=0.7,
            max_tokens=50,
            n=1,
            stop=None,
            timeout=15,
        ))
        response_text = response.choices[0].text.strip().split('\n')[0]
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        raise HTTPException(status_code=500, detail='Error processing message')

    return response_text


# Send a message to the specified Slack channel
async def send_message(channel, text):
    try:
        await slack_client.chat_postMessage(channel=channel, text=text)
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        raise HTTPException(status_code=500, detail='Error sending message')


# Run the app
if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=3000)

