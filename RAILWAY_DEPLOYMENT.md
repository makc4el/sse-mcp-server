# Railway Deployment Guide for SSE MCP Server

## 🚨 **Issue Fixed: Dependency Conflict Resolution**

The Railway deployment error was caused by conflicting package dependencies:
- `fastapi==0.104.1` required `anyio<4.0.0,>=3.7.1`
- `mcp==1.0.0` required `anyio>=4.6`

### ✅ **Solution Applied**

1. **Updated requirements.txt** with compatible versions
2. **Removed conflicting mcp package** (not needed since we implement MCP protocol directly)
3. **Added explicit anyio version constraint**
4. **Updated to newer, compatible package versions**

## 📋 **Fixed requirements.txt**

```txt
# Compatible versions that resolve dependency conflicts
fastapi>=0.108.0
uvicorn>=0.25.0
pydantic>=2.6.0
httpx>=0.26.0
python-multipart>=0.0.6

# Production deployment compatible versions
anyio>=3.7.1,<4.0.0
```

## 🚀 **Railway Deployment Steps**

### **1. Pre-deployment Checklist**
- ✅ Dependencies conflict resolved
- ✅ PORT environment variable handling configured
- ✅ Health check endpoint available at `/health`
- ✅ Railway configuration files updated

### **2. Deploy to Railway**

```bash
# 1. Commit the fixes
git add .
git commit -m "Fix dependency conflicts for Railway deployment"

# 2. Push to Railway (if connected via GitHub)
git push origin main

# 3. Or deploy directly to Railway
railway up
```

### **3. Environment Variables**

Railway will automatically set:
- `PORT` - Application port (handled automatically)
- `HOST` - Set to `0.0.0.0` in railway.json

### **4. Health Check**

Railway will use the health check endpoint:
- **URL**: `https://your-app.railway.app/health`
- **Expected Response**: `{"status":"healthy","server":"sse-mcp-server"}`

## 🔧 **Configuration Files**

### **railway.json**
```json
{
  "deploy": {
    "startCommand": "python main.py",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 100,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

### **main.py (PORT handling)**
```python
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))  # Railway sets PORT
    host = os.environ.get("HOST", "0.0.0.0")
    
    uvicorn.run("main:app", host=host, port=port)
```

## 🧪 **Testing After Deployment**

### **1. Health Check**
```bash
curl https://your-app.railway.app/health
# Expected: {"status":"healthy","server":"sse-mcp-server"}
```

### **2. Server Info**
```bash
curl https://your-app.railway.app/
# Expected: Server info with endpoints
```

### **3. SSE Connection Test**
```bash
curl -N -H "Accept: text/event-stream" https://your-app.railway.app/connect
# Expected: SSE events with endpoint information
```

### **4. MCP Client Test**
Update your MCP client to use the Railway URL:
```python
client = SSEMCPClient("https://your-app.railway.app")
```

## 🐛 **Troubleshooting**

### **If Deployment Still Fails:**

1. **Check Railway Logs:**
```bash
railway logs
```

2. **Common Issues:**
   - Port binding: Ensure `HOST=0.0.0.0`
   - Dependencies: Run `pip install -r requirements.txt` locally first
   - Health check: Verify `/health` endpoint works

3. **Force Rebuild:**
```bash
railway up --detach
```

### **Dependency Conflicts:**
```bash
# Test locally first
pip install --dry-run -r requirements.txt

# If conflicts, check with:
pip-tools compile requirements.in
```

## 🌐 **Production Configuration**

### **Environment Variables in Railway:**
- `PYTHONUNBUFFERED=1` (for real-time logs)
- `HOST=0.0.0.0` (for external access)

### **Scaling:**
- Railway will auto-scale based on usage
- SSE connections are stateless and scale horizontally
- Each connection gets a unique session ID

### **SSL/HTTPS:**
- Railway provides HTTPS automatically
- Update MCP client URLs to use `https://`

## 📊 **Monitoring**

### **Railway Dashboard:**
- CPU usage
- Memory usage
- Request metrics
- Error rates

### **Application Logs:**
```bash
railway logs --tail
```

### **Health Monitoring:**
The `/health` endpoint provides:
```json
{
  "status": "healthy",
  "server": "sse-mcp-server",
  "timestamp": "2024-01-01T00:00:00Z",
  "uptime": "24h 30m"
}
```

## ✅ **Deployment Success Checklist**

- [ ] Dependencies install without conflicts
- [ ] Server starts and binds to Railway PORT
- [ ] Health check returns 200 OK
- [ ] SSE connections work from external clients
- [ ] MCP protocol functions correctly
- [ ] Tools can be listed and called
- [ ] Real-time notifications work

## 🔗 **Next Steps**

1. **Update MCP client**: Change server URL to Railway deployment
2. **Test integration**: Verify LangChain + MCP works with deployed server
3. **Monitor**: Set up alerts for health check failures
4. **Scale**: Configure auto-scaling if needed

Your SSE MCP server is now ready for production deployment on Railway! 🎉

