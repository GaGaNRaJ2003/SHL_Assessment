# Deploy to Replit (Easiest Option!)

## Steps:

1. **Go to Replit**: https://replit.com
2. **Sign up/Login** (free account)
3. **Click**: "Create Repl" → "Import from GitHub"
4. **Paste**: `https://github.com/GaGaNRaJ2003/SHL_Assessment`
5. **Click**: "Import"
6. **Wait**: Replit will clone your repo
7. **Set Environment Variable**:
   - Click "Secrets" (lock icon in sidebar)
   - Add: `GEMINI_API_KEY` = your API key
8. **Click**: "Run" button
9. **Get URL**: Replit gives you a public URL like `https://your-app.repl.co`

## That's it! No configuration needed!

Replit auto-detects FastAPI and runs it. The URL is public and works immediately.

## Note:
- First API call will take 5-10 minutes (generates embeddings)
- Free tier has some limitations but perfect for demo
- URL is permanent (doesn't change)

