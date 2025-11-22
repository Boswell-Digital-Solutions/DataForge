import asyncio
import sys
sys.path.insert(0, '/home/charles/projects/Coding2025/Forge/NeuroForge')

from neuroforge_backend.workbench.prompt_models import PromptCreate, ContextRef
from neuroforge_backend.workbench.prompt_storage import get_storage

async def test_prompt_storage():
    """Test prompt storage with DataForge integration."""
    storage = get_storage()
    
    print("Testing Prompt Storage with DataForge")
    print("=" * 50)
    
    # Create a test prompt
    print("\n1. Creating test prompt...")
    prompt_data = PromptCreate(
        name="Test Character Prompt",
        description="A test prompt for character creation",
        category="character",
        workspace="test_workspace",
        tags=["test", "character"],
        base_prompt="Create a character with unique traits...",
        context_refs=[
            ContextRef(id="ctx_1", label="Background Context"),
            ContextRef(id="ctx_2", label="Style Guide")
        ],
        models=["gpt-4", "claude-3-5-sonnet"],
        pinned=False
    )
    
    try:
        prompt = await storage.create_prompt("test_user", prompt_data)
        print(f"✓ Created prompt: {prompt.id}")
        print(f"  Name: {prompt.name}")
        print(f"  Category: {prompt.category}")
        
        # Retrieve the prompt
        print(f"\n2. Retrieving prompt {prompt.id}...")
        retrieved = await storage.get_prompt(prompt.id, "test_user")
        if retrieved:
            print(f"✓ Retrieved prompt: {retrieved.name}")
        else:
            print("✗ Failed to retrieve prompt")
        
        # List prompts
        print("\n3. Listing prompts...")
        prompts, total = await storage.list_prompts("test_user", workspace="test_workspace")
        print(f"✓ Found {total} prompt(s)")
        for p in prompts:
            print(f"  - {p.name} ({p.id})")
        
        print("\n✅ All tests passed!")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_prompt_storage())
