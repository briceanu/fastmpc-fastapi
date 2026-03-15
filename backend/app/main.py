from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import router
from app.mcp_server import mcp  # your FastMCP instance

mcp_app = mcp.http_app(path="/")


app = FastAPI(
    title="Agentic RAG API",
    version="0.1.0",
    description="""
        API providing agentic RAG system:
        - Document upload
        - Semantic search via Pinecone
        - Conversation tracking with checkpoints
    """,
    lifespan=mcp_app.lifespan
)

app.include_router(router)

app.mount('/mcp', mcp_app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
