from fastmcp.client.transports import StreamableHttpTransport
from fastmcp import Client
from app.logger import logger
from fastapi import UploadFile, status, HTTPException
from app.celery_tasks import upload_file_task
import os
from dotenv import load_dotenv
from pinecone import NotFoundException
from app.schemas import GptScheamOut, UploadFileSchemaOut, RemoveNamespaceSchemaOut
from app.celery_tasks import pc
from dotenv import load_dotenv
from app.aws_secretes import get_secret
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_mcp_adapters.tools import load_mcp_tools

from langchain_openai.chat_models import ChatOpenAI
import uuid

from app.middleware import ContentFilterMiddleware

load_dotenv()
environment = os.getenv('ENVIRONMENT')

# loading secrets from aws in production
if environment == 'production':

    secrets = get_secret()

    INDEX_NAME = secrets["INDEX_NAME"]
    OPENAI_API_KEY = secrets["OPENAI_API_KEY"]

# loading environment variables for development
if environment == 'development':

    INDEX_NAME = os.getenv("INDEX_NAME")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")
POSTGRES_DB = os.getenv("POSTGRES_DB")


transport = StreamableHttpTransport(
    url="http://localhost:8000/mcp",
)
client = Client(transport)


# DB_URI = f'postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}'


async def upload_file_logic(user_file: UploadFile, category: str) -> UploadFileSchemaOut:
    """
    Handle an uploaded file asynchronously by reading its contents and delegating
    the processing to a background Celery task.

    Steps performed:
    - Read the uploaded file from the client.
    - Decode it as UTF-8 text.
    - Trigger the `upload_file_task` Celery task with the file contents and category.
    - Return a success response immediately without waiting for the task to finish.

    Parameters
    ----------
    user_file : UploadFile
        The file uploaded by the client.
    category : str
        The category used by the background task to classify or process the data.

    Returns
    -------
    UploadFileSchemaOut
        A schema indicating that the file was successfully submitted for processing.
    """
    document = await user_file.read()
    decoded_document = document.decode('utf-8')

    upload_file_task.delay(
        decoded_document=decoded_document, category=category)
    return UploadFileSchemaOut(success='data uploaded')


async def remove_namespace(namespace: str) -> RemoveNamespaceSchemaOut:
    """
    Remove a namespace from the vector index.

    This function connects to the configured Pinecone index and attempts to
    delete the specified namespace. If the namespace exists, it is removed and
    a success response is returned. If the namespace does not exist, an HTTP
    400 error is raised.

    Parameters
    ----------
    namespace : str
        The name of the namespace to delete.

    Returns
    -------
    RemoveNamespaceSchemaOut
        A schema object containing a confirmation message indicating that the
        namespace was successfully removed.

    Raises
    ------
    HTTPException
        Raised with status code 400 if the namespace does not exist.
    """
    try:
        index = pc.Index(name=INDEX_NAME)
        index.delete_namespace(namespace=namespace)
        return RemoveNamespaceSchemaOut(response=f'Namespce {namespace} successfully reomved.')

    except NotFoundException:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f'Namespace {namespace} not found.')


async def agent_response(question: str):

    system_prompt = """
        You are an expert virtual assistant with access to two tools:
        1. `search_cars_vectors(question: str, name_space: str)` - Searches semantic data about cars.
        2. `search_addresses_vectors(question: str, name_space: str)` - Searches semantic data about addresses or people.

        You also have a tool `retrive_all_name_spaces()` that returns all available namespaces.

        Your job is to:
        - First, call `retrive_all_name_spaces()` to see which namespaces exist.
        - Analyze the user question and determine if it is about cars or addresses/people.
        - Select the correct namespace from the list.
        - Call the appropriate tool for the question, using the chosen namespace.
        - Respond concisely with the most relevant information returned by the tool.

        Rules:
        - Always use the tools first before answering.
        - Only provide information found in the vector database.
        - If the question is about cars, use `search_cars_vectors`.
        - If the question is about addresses or people, use `search_addresses_vectors`.
        - If you cannot determine the topic, politely ask the user for clarification.
        - Format your final answer in clear, concise text.
        """

    model = ChatOpenAI(
        model='gpt-4.1',
        api_key=OPENAI_API_KEY,
        temperature=0.1,
        max_tokens=1000,
        timeout=30,
    )

    async with client:
        tools = await load_mcp_tools(client.session)
        agent = create_agent(model=model, tools=tools, middleware=[
            ContentFilterMiddleware(
                banned_keywords=["hack", "exploit", "malware",
                                 "bomb", "remote code execution"]
            )
        ],
            system_prompt=system_prompt)
        response = await agent.ainvoke({'messages': [HumanMessage(content=question)]})

    return response['messages'][-1].content
