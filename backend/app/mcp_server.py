from fastapi import HTTPException, status
from fastmcp import FastMCP
from pinecone import PineconeException, SearchQuery
from app.pinecone_client import pc
from dotenv import load_dotenv
from app.aws_secretes import get_secret
import os
from app.logger import logger

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


mcp = FastMCP("RAG Tools")


@mcp.tool(description='Retvives all namespaces from index')
def retrive_all_name_spaces():
    try:
        index = pc.Index(name=index_name)
        namespaces = [ns["name"] for ns in index.list_namespaces()]
        return namespaces

    except PineconeException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'An error occurred: {str(e)}'
        )


@mcp.tool(description="Search semantic data about cars from the vector database")
def search_cars_vectors(question: str, name_space: str):
    try:
        idx = pc.Index(INDEX_NAME)
        response = idx.search(
            namespace=name_space,
            query=SearchQuery(inputs={"text": question}, top_k=3),
        )
        return [{"id": h._id, "score": h._score, "fields": h.fields} for h in response.result.hits]
    except PineconeException as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f'An error occured: {str(e)}')


@mcp.tool(description="Search semantic data about addresses from the vector database")
def search_addresses_vectors(question: str, name_space: str):
    try:
        idx = pc.Index(INDEX_NAME)
        response = idx.search(
            namespace=name_space,
            query=SearchQuery(inputs={"text": question}, top_k=3),
        )
        return [{"id": h._id, "score": h._score, "fields": h.fields} for h in response.result.hits]
    except PineconeException as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f'An error occured: {str(e)}')
