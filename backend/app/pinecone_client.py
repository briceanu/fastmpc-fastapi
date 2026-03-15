import os
from pinecone import Pinecone
# from aws_secretes import get_secret
from app.aws_secretes import get_secret
from dotenv import load_dotenv
load_dotenv()
environment = os.getenv('ENVIRONMENT')

# loading secrets from aws in production
if environment == 'production':

    secrets = get_secret()
    PINECONE_API_KEY = secrets["PINECONE_API_KEY"]

# loading environment variables for development
if environment == 'development':
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")


pc = Pinecone(api_key=PINECONE_API_KEY)
