# 🚨 Railway Deployment Fix Guide

## **Problem Identified**
Railway is failing with dependency conflicts that we already fixed. The error shows:
```
fastapi 0.104.1 depends on anyio<4.0.0 and >=3.7.1
mcp 1.0.0 depends on anyio>=4.6
```

But our `requirements.txt` already has:
- ✅ `fastapi>=0.108.0` (updated)
- ✅ Removed `mcp==1.0.0` (conflicting package)
- ✅ Added `anyio>=3.7.1,<4.0.0` (explicit constraint)

## 🔍 **Root Cause**
Railway is deploying from the **wrong location** or using **cached build data**.

## 🛠️ **Immediate Fix Steps**

### **Step 1: Verify Railway Configuration**
Check Railway dashboard:
1. **Service Directory**: Should be `sse-mcp-server/` (not root or client)
2. **Branch**: Should be `modarchenko/basic-mcp`
3. **Build Command**: Should use `requirements.txt` from server directory

### **Step 2: Force Rebuild**
In Railway dashboard:
1. Go to your service
2. Click **"Deployments"**
3. Click **"Redeploy"** or **"Force Rebuild"**
4. Clear any cached dependencies

### **Step 3: Verify Correct Source**
Railway should be reading from:
```
/sse-mcp-server/requirements.txt  ✅ CORRECT
```
NOT from:
```
/sse-mcp-client/requirements.txt  ❌ WRONG
/requirements.txt (root)          ❌ WRONG
```

### **Step 4: Manual Deployment Check**
```bash
# Test locally first
cd sse-mcp-server
pip install -r requirements.txt  # Should work without conflicts
python main.py                   # Should start successfully
```

## 🔧 **Railway Configuration Files**

### **Verify railway.json**
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "python main.py",
    "healthcheckPath": "/health", 
    "healthcheckTimeout": 100,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

### **Expected Build Process**
Railway should detect:
1. **Python 3.11** environment
2. **requirements.txt** (fixed version)
3. **main.py** as entry point
4. **Port** from environment variable

## 📋 **Dependency Verification**

### **Current Fixed Requirements**
```txt
fastapi>=0.108.0          # ✅ Updated, compatible
uvicorn>=0.25.0          # ✅ Compatible
pydantic>=2.6.0          # ✅ Compatible  
httpx>=0.26.0            # ✅ Compatible
python-multipart>=0.0.6  # ✅ Compatible
anyio>=3.7.1,<4.0.0     # ✅ Explicit constraint
```

### **Removed Conflicting Package**
```txt
mcp==1.0.0  # ❌ REMOVED - was causing anyio conflicts
```

## 🚀 **Alternative Deployment Options**

### **Option 1: Railway with Root Detection**
```bash
# Create railway.toml in project root
[build]
command = "pip install -r sse-mcp-server/requirements.txt"

[deploy]
command = "cd sse-mcp-server && python main.py"
```

### **Option 2: Docker Deployment**
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY sse-mcp-server/requirements.txt .
RUN pip install -r requirements.txt

COPY sse-mcp-server/ .
EXPOSE $PORT

CMD ["python", "main.py"]
```

### **Option 3: Manual File Copy**
```bash
# Copy server files to root for Railway
cp sse-mcp-server/* .
git add .
git commit -m "Move server files to root for Railway"
git push
```

## 🔍 **Debugging Commands**

### **Check What Railway Sees**
```bash
# Verify requirements.txt content
cat sse-mcp-server/requirements.txt

# Test dependency installation
cd sse-mcp-server
python -m venv test_env
source test_env/bin/activate
pip install -r requirements.txt
```

### **Verify Git State**
```bash
# Check latest commit
git log --oneline -5

# Verify requirements in git
git show HEAD:sse-mcp-server/requirements.txt
```

## ✅ **Success Indicators**

After fix, Railway logs should show:
```
✅ Installing fastapi>=0.108.0
✅ Installing uvicorn>=0.25.0  
✅ Installing pydantic>=2.6.0
✅ No mcp package (removed)
✅ Server starts successfully
✅ Health check responds at /health
```

## 🚨 **If Still Failing**

1. **Clear Railway Cache**
2. **Create New Railway Service** pointing to `sse-mcp-server/`
3. **Deploy from Different Branch**
4. **Contact Railway Support** with build logs

## 📞 **Quick Fix Commands**

```bash
# 1. Verify local requirements work
cd sse-mcp-server && pip install -r requirements.txt

# 2. Force git push (if needed)
git push origin modarchenko/basic-mcp --force-with-lease

# 3. Test server locally
python main.py

# 4. Check Railway deployment logs
railway logs --tail
```

The fix should resolve the anyio dependency conflict and allow successful Railway deployment! 🎉
