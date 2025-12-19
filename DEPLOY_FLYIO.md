# Deploy to Fly.io (Best Free Option)

## Prerequisites:
1. Sign up at https://fly.io (free)
2. Install flyctl:
   ```bash
   # Windows (PowerShell)
   iwr https://fly.io/install.ps1 -useb | iex
   
   # Or download from: https://fly.io/docs/hands-on/install-flyctl/
   ```

## Steps:

1. **Login to Fly.io**:
   ```bash
   flyctl auth login
   ```

2. **Initialize Fly.io app** (in your project directory):
   ```bash
   cd "C:\Users\Gagan Raj Singh\Desktop\SHL"
   flyctl launch
   ```
   - App name: `shl-assessment-api` (or any name)
   - Region: Choose closest (e.g., `iad` for US East)
   - PostgreSQL: No
   - Redis: No

3. **Set environment variable**:
   ```bash
   flyctl secrets set GEMINI_API_KEY=your_api_key_here
   ```

4. **Deploy**:
   ```bash
   flyctl deploy
   ```

5. **Get your URL**:
   ```bash
   flyctl open
   ```
   Or check dashboard: https://fly.io/dashboard

## Your API will be at:
`https://shl-assessment-api.fly.dev`

## Benefits:
- ✅ Free tier (3 VMs)
- ✅ Reliable
- ✅ Fast deployments
- ✅ No credit card needed

