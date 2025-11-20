"""
Setup DataForge domains for multi-genre support

This script creates the necessary domains in DataForge for:
- Fantasy fiction
- Sci-Fi fiction
- Christian fiction
- General writing craft

Prerequisites:
- DataForge must be running on DATAFORGE_URL
- You must have admin credentials for DataForge
"""

import os
import sys
import httpx
from dotenv import load_dotenv

# Load environment
load_dotenv()

DATAFORGE_URL = os.getenv("DATAFORGE_URL", "http://localhost:8001")
DATAFORGE_ADMIN_USERNAME = os.getenv("DATAFORGE_ADMIN_USERNAME", "admin")
DATAFORGE_ADMIN_PASSWORD = os.getenv("DATAFORGE_ADMIN_PASSWORD")


# Domain definitions
DOMAINS = [
    {
        "domain_id": "writing_craft",
        "name": "Writing Craft",
        "description": "Universal writing techniques - dialogue, pacing, structure, POV, character development"
    },
    {
        "domain_id": "fantasy_craft",
        "name": "Fantasy Writing",
        "description": "Fantasy-specific techniques - magic systems, worldbuilding, creatures, mythology, epic storytelling"
    },
    {
        "domain_id": "scifi_craft",
        "name": "Science Fiction Writing",
        "description": "Sci-fi techniques - technology systems, hard science, space opera, alien cultures, future societies"
    },
    {
        "domain_id": "christian_fiction_craft",
        "name": "Christian Fiction Writing",
        "description": "Christian fiction techniques - biblical themes, spiritual journeys, faith integration, redemptive arcs"
    },
    {
        "domain_id": "worldbuilding",
        "name": "Worldbuilding",
        "description": "World creation for fantasy and sci-fi - cultures, geography, history, societies, economics"
    },
    {
        "domain_id": "biblical_themes",
        "name": "Biblical Themes",
        "description": "Biblical narratives, themes, and scripture connections for Christian fiction"
    },
]


def get_auth_token(username: str, password: str) -> str:
    """Authenticate with DataForge and get access token"""
    print(f"Authenticating with DataForge as '{username}'...")

    try:
        response = httpx.post(
            f"{DATAFORGE_URL}/auth/token",
            data={
                "username": username,
                "password": password
            },
            timeout=10.0
        )

        if response.status_code == 200:
            data = response.json()
            print("✅ Authentication successful")
            return data["access_token"]
        else:
            print(f"❌ Authentication failed: {response.status_code}")
            print(f"Response: {response.text}")
            sys.exit(1)

    except Exception as e:
        print(f"❌ Error authenticating: {e}")
        sys.exit(1)


def create_domain(token: str, domain: dict) -> bool:
    """Create a domain in DataForge"""
    print(f"\nCreating domain: {domain['name']} ({domain['domain_id']})...")

    try:
        response = httpx.post(
            f"{DATAFORGE_URL}/admin/domains",
            headers={"Authorization": f"Bearer {token}"},
            json=domain,
            timeout=10.0
        )

        if response.status_code in [200, 201]:
            print(f"✅ Created: {domain['name']}")
            return True
        elif response.status_code == 409:
            print(f"⚠️  Already exists: {domain['name']}")
            return True
        else:
            print(f"❌ Failed to create {domain['name']}: {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Error creating domain {domain['name']}: {e}")
        return False


def verify_domains(token: str) -> None:
    """Verify all domains were created"""
    print("\n" + "="*60)
    print("Verifying domains...")
    print("="*60)

    try:
        response = httpx.get(
            f"{DATAFORGE_URL}/admin/domains",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0
        )

        if response.status_code == 200:
            domains = response.json()
            print(f"\n✅ Total domains in DataForge: {len(domains)}")
            print("\nDomains:")
            for domain in domains:
                print(f"  - {domain['name']} ({domain['domain_id']})")
        else:
            print(f"⚠️  Could not verify domains: {response.status_code}")

    except Exception as e:
        print(f"⚠️  Error verifying domains: {e}")


def main():
    """Main setup function"""
    print("="*60)
    print("DataForge Multi-Genre Domain Setup")
    print("="*60)
    print(f"DataForge URL: {DATAFORGE_URL}")
    print()

    # Check if password is provided
    if not DATAFORGE_ADMIN_PASSWORD:
        print("❌ Error: DATAFORGE_ADMIN_PASSWORD not set in .env")
        print("\nPlease set your DataForge admin password:")
        print("  export DATAFORGE_ADMIN_PASSWORD='your-password'")
        print("Or add to .env file:")
        print("  DATAFORGE_ADMIN_PASSWORD=your-password")
        sys.exit(1)

    # Check DataForge health
    print("Checking DataForge health...")
    try:
        response = httpx.get(f"{DATAFORGE_URL}/health", timeout=5.0)
        if response.status_code == 200:
            print("✅ DataForge is running")
        else:
            print(f"⚠️  DataForge returned status: {response.status_code}")
    except Exception as e:
        print(f"❌ Cannot connect to DataForge: {e}")
        print("\nMake sure DataForge is running:")
        print("  cd ../DataForge")
        print("  uvicorn app.main:app --port 8001")
        sys.exit(1)

    # Authenticate
    token = get_auth_token(DATAFORGE_ADMIN_USERNAME, DATAFORGE_ADMIN_PASSWORD)

    # Create domains
    print("\n" + "="*60)
    print("Creating domains...")
    print("="*60)

    success_count = 0
    for domain in DOMAINS:
        if create_domain(token, domain):
            success_count += 1

    print(f"\n✅ Successfully created/verified {success_count}/{len(DOMAINS)} domains")

    # Verify
    verify_domains(token)

    print("\n" + "="*60)
    print("Setup complete!")
    print("="*60)
    print("\nNext steps:")
    print("1. Upload writing craft content to DataForge domains")
    print("2. Use the DataForge admin UI at: http://localhost:8001/admin")
    print("3. Test AuthorForge research queries")
    print("\nExample command to upload a document:")
    print("  curl -X POST http://localhost:8001/admin/documents \\")
    print("    -H 'Authorization: Bearer YOUR_TOKEN' \\")
    print("    -F 'file=@your_document.pdf' \\")
    print("    -F 'domain_id=fantasy_craft' \\")
    print("    -F 'title=Magic System Design Guide'")


if __name__ == "__main__":
    main()
