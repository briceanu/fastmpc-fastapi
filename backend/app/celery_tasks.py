from app.logger import logger
from celery import Celery
import os
from fastapi import UploadFile
from pinecone import IndexEmbed, Metric, Pinecone, PineconeException, ServerlessSpec
from app.aws_secretes import get_secret
from langchain_text_splitters import CharacterTextSplitter
from dotenv import load_dotenv
from app.pinecone_client import pc
load_dotenv()
environment = os.getenv('ENVIRONMENT')

# loading secrets from aws in production
if environment == 'production':

    secrets = get_secret()

    REDIS_HOST = secrets["REDIS_HOST"]
    REDIS_PORT = secrets["REDIS_PORT"]
    INDEX_NAME = secrets["INDEX_NAME"]
    PINECONE_REGION = secrets["PINECONE_REGION"]
    PINECONE_CLOUD = secrets["PINECONE_CLOUD"]

# loading environment variables for development
if environment == 'development':
    REDIS_HOST = os.getenv("REDIS_HOST")
    REDIS_PORT = os.getenv("REDIS_PORT")
    INDEX_NAME = os.getenv("INDEX_NAME")
    PINECONE_REGION = os.getenv("PINECONE_REGION")
    PINECONE_CLOUD = os.getenv("PINECONE_CLOUD")

broker = f'redis://{REDIS_HOST}:{REDIS_PORT}/1'
backend = f'redis://{REDIS_HOST}:{REDIS_PORT}/2'

index_name = INDEX_NAME


app = Celery(broker=broker, backend=backend)


@app.task(bind=True,  max_retries=5)
def upload_file_task(self, decoded_document: UploadFile, category: str):
    """
    Celery task to split a text document into chunks and upload them to a Pinecone vector index.

    This task:
    1. Splits the provided document into smaller chunks using a CharacterTextSplitter.
    2. Checks if the specified Pinecone index exists; if not, creates it with the appropriate embedding model and metric.
    3. Prepares each chunk as a record with a unique ID.
    4. Uploads all chunks to the Pinecone index under the specified namespace/category.
    5. Handles errors gracefully: retries on general exceptions, returns Pinecone-specific errors.

    Args:
        decoded_document (str): The text content of the document to be uploaded.
        category (str): The namespace under which the document chunks will be stored in Pinecone.

    Returns:
        str or dict: Returns 'Data uploaded successfully' on success. Returns a dictionary with an error message if a PineconeException occurs.

    Raises:
        self.retry: Retries the task on general exceptions, with a countdown of 5 seconds, up to 4 retries.
    """

    try:
        spliter = CharacterTextSplitter(
            separator='- - - - - - - - - -', chunk_size=200, chunk_overlap=0)
        chunks = spliter.split_text(decoded_document)
        if not pc.has_index(name=index_name):
            logger.info("Index does not exist, creating...")
            pc.create_index_for_model(
                name=index_name,
                cloud=PINECONE_CLOUD,
                region=PINECONE_REGION,
                embed=IndexEmbed(
                    model='llama-text-embed-v2',
                    metric=Metric.COSINE,
                    field_map={
                        "text": "chunk",
                    },
                )
            )

        documents = [{'_id': f'chunk-{i}', 'chunk': chunk}
                     for i, chunk in enumerate(chunks)]
        dense_index = pc.Index(name=index_name)

        dense_index.upsert_records(namespace=category, records=documents)
        logger.info('Data uploaded successfuly')
        return 'Data uploaded successfully'
    except PineconeException as e:
        return {"error": str(e)}

    except Exception as exc:
        raise self.retry(exc=exc, countdown=5)
