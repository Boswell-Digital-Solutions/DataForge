#!/bin/bash

################################################################################
# FORGE ECOSYSTEM - CLAUDE INTEGRATION SETUP
################################################################################
#
# This script installs Claude context files and VS Code settings
# for the Forge Ecosystem project.
#
# Usage: ./setup_claude_integration.sh
#
################################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_header() {
    echo -e "${BLUE}=================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}=================================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

################################################################################
# MAIN SCRIPT
################################################################################

print_header "Forge Ecosystem - Claude Integration Setup"

# Check if we're in the right directory
if [ ! -d ".git" ]; then
    print_error "Not in a git repository. Please run this from your Forge project root."
    exit 1
fi

# Create backup directory
BACKUP_DIR=".claude-backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"
print_info "Backup directory created: $BACKUP_DIR"

################################################################################
# 1. INSTALL PROJECT CONTEXT FILE
################################################################################

print_header "Installing Project Context File"

if [ -f ".claude_project_context.md" ]; then
    print_warning "Existing .claude_project_context.md found. Backing up..."
    cp .claude_project_context.md "$BACKUP_DIR/"
fi

cp /tmp/.claude_project_context.md ./
print_success "Installed .claude_project_context.md"

################################################################################
# 2. INSTALL CUSTOM INSTRUCTIONS FILE
################################################################################

print_header "Installing Custom Instructions File"

if [ -f "CLAUDE_CUSTOM_INSTRUCTIONS.md" ]; then
    print_warning "Existing CLAUDE_CUSTOM_INSTRUCTIONS.md found. Backing up..."
    cp CLAUDE_CUSTOM_INSTRUCTIONS.md "$BACKUP_DIR/"
fi

cp /tmp/CLAUDE_CUSTOM_INSTRUCTIONS.md ./
print_success "Installed CLAUDE_CUSTOM_INSTRUCTIONS.md"

################################################################################
# 3. INSTALL VS CODE SETTINGS
################################################################################

print_header "Installing VS Code Settings"

# Create .vscode directory if it doesn't exist
mkdir -p .vscode

if [ -f ".vscode/settings.json" ]; then
    print_warning "Existing .vscode/settings.json found. Backing up..."
    cp .vscode/settings.json "$BACKUP_DIR/"
fi

cp /tmp/.vscode-settings.json .vscode/settings.json
print_success "Installed .vscode/settings.json"

################################################################################
# 4. INSTALL README
################################################################################

print_header "Installing Integration README"

if [ -f "CLAUDE_INTEGRATION_README.md" ]; then
    print_warning "Existing CLAUDE_INTEGRATION_README.md found. Backing up..."
    cp CLAUDE_INTEGRATION_README.md "$BACKUP_DIR/"
fi

cp /tmp/CLAUDE_INTEGRATION_README.md ./
print_success "Installed CLAUDE_INTEGRATION_README.md"

################################################################################
# 5. UPDATE .gitignore
################################################################################

print_header "Updating .gitignore"

if [ -f ".gitignore" ]; then
    if ! grep -q ".claude_project_context.md" .gitignore; then
        echo "" >> .gitignore
        echo "# Claude Integration Files (keep in repo)" >> .gitignore
        echo "!.claude_project_context.md" >> .gitignore
        echo "!CLAUDE_CUSTOM_INSTRUCTIONS.md" >> .gitignore
        echo "!CLAUDE_INTEGRATION_README.md" >> .gitignore
        print_success "Updated .gitignore"
    else
        print_info ".gitignore already includes Claude files"
    fi
else
    print_warning "No .gitignore found. Consider creating one."
fi

################################################################################
# 6. VERIFY INSTALLATION
################################################################################

print_header "Verifying Installation"

FILES_TO_CHECK=(
    ".claude_project_context.md"
    "CLAUDE_CUSTOM_INSTRUCTIONS.md"
    "CLAUDE_INTEGRATION_README.md"
    ".vscode/settings.json"
)

ALL_GOOD=true

for file in "${FILES_TO_CHECK[@]}"; do
    if [ -f "$file" ]; then
        print_success "$file installed"
    else
        print_error "$file NOT found"
        ALL_GOOD=false
    fi
done

################################################################################
# 7. FINAL INSTRUCTIONS
################################################################################

echo ""
print_header "Installation Complete!"
echo ""

if [ "$ALL_GOOD" = true ]; then
    print_success "All files installed successfully!"
    echo ""
    print_info "Next Steps:"
    echo ""
    echo "1. Read CLAUDE_INTEGRATION_README.md for usage instructions"
    echo "2. Open VS Code: code ."
    echo "3. Start a conversation with Claude and upload .claude_project_context.md"
    echo ""
    print_info "Claude Desktop App Users:"
    echo "   - Create a new Project: 'Forge Ecosystem'"
    echo "   - Add .claude_project_context.md to Project Knowledge"
    echo "   - Add CLAUDE_CUSTOM_INSTRUCTIONS.md to Project Knowledge"
    echo ""
    print_info "Backups (if any) saved to: $BACKUP_DIR"
else
    print_error "Some files failed to install. Check the output above."
    exit 1
fi

echo ""
print_header "Happy Coding! 🚀"
echo ""
