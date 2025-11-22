"""
Test script for prompt and version API endpoints
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sys
sys.path.insert(0, '/home/charles/projects/Coding2025/Forge/NeuroForge')

from neuroforge_backend.workbench.prompt_router import router as prompt_router
from neuroforge_backend.workbench.version_router import router as version_router
from neuroforge_backend.workbench.estimation_router import router as estimation_router
from neuroforge_backend.workbench.deployment_router import router as deployment_router
from neuroforge_backend.workbench.chain_router import router as chain_router
from neuroforge_backend.workbench.execution_router import router as execution_router

app = FastAPI(title="VibeForge Workbench API Test")

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(prompt_router, prefix="/api/v1/workbench")
app.include_router(version_router, prefix="/api/v1/workbench")
app.include_router(estimation_router, prefix="/api/v1/workbench")
app.include_router(deployment_router, prefix="/api/v1/workbench")
app.include_router(chain_router, prefix="/api/v1/workbench")
app.include_router(execution_router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn
    print("Starting VibeForge Workbench test server at http://localhost:8000")
    print("API docs available at http://localhost:8000/docs")
    print("\nEndpoints:")
    print("  Models: /api/v1/models")
    print("  Execute: /api/v1/execute")
    print("  Prompts: /api/v1/workbench/prompts")
    print("  Versions: /api/v1/workbench/prompts/{id}/versions")
    print("  Estimation: /api/v1/workbench/estimate")
    print("  Deployments: /api/v1/workbench/prompts/{id}/deploy")
    print("  Chains: /api/v1/workbench/chains")
    print("  Executions: /api/v1/executions")
    uvicorn.run(app, host="127.0.0.1", port=8000)
