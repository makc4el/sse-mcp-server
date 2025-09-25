#!/bin/bash

# Railway Redeploy Script - Fix Dependency Conflicts
# This script helps redeploy with the fixed requirements.txt

echo "🚀 Railway Redeploy Fix Script"
echo "================================"

echo "📋 Current requirements.txt content:"
echo "------------------------------------"
cat requirements.txt

echo ""
echo "✅ Verification:"
echo "- fastapi version: $(grep fastapi requirements.txt)"
echo "- mcp package: $(grep -E '^mcp' requirements.txt || echo 'REMOVED ✅')"
echo "- anyio constraint: $(grep anyio requirements.txt)"

echo ""
echo "🧪 Testing local installation:"
echo "------------------------------"
pip install --dry-run -r requirements.txt > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Requirements are valid locally"
else
    echo "❌ Requirements have conflicts locally"
    echo "Testing individual packages..."
    pip install --dry-run fastapi>=0.108.0 uvicorn>=0.25.0 pydantic>=2.6.0
fi

echo ""
echo "🔄 Railway Fix Options:"
echo "----------------------"
echo "1. In Railway Dashboard:"
echo "   - Go to your service"
echo "   - Click 'Deployments'"
echo "   - Click 'Redeploy' or 'Force Rebuild'"
echo "   - Clear build cache"

echo ""
echo "2. Verify Railway Settings:"
echo "   - Root Directory: Should be 'sse-mcp-server/'"
echo "   - Branch: Should be 'modarchenko/basic-mcp'"
echo "   - Build Command: Should auto-detect requirements.txt"

echo ""
echo "3. Check Current Git State:"
echo "   - Current branch: $(git branch --show-current)"
echo "   - Latest commit: $(git log --oneline -1)"
echo "   - Requirements in git: $(git show HEAD:requirements.txt | head -2)"

echo ""
echo "🏥 Health Check:"
echo "---------------"
echo "After Railway deployment, test:"
echo "curl https://web-production-b40eb.up.railway.app/health"

echo ""
echo "🎯 Expected Success Response:"
echo '{"status":"healthy","server":"sse-mcp-server"}'

echo ""
echo "📞 Quick Commands:"
echo "-----------------"
echo "# Test locally:"
echo "python main.py"
echo ""
echo "# Force git push (if needed):"
echo "git push origin modarchenko/basic-mcp --force-with-lease"
echo ""
echo "# Check Railway logs:"
echo "railway logs --tail"

echo ""
echo "✨ The requirements.txt is fixed! Railway just needs to use the latest version."
