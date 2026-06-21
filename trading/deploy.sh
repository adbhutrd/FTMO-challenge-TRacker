#!/bin/bash
# Deploy FTMO Tracker & BugFlow SaaS to Netlify/GitHub Pages
# Usage: bash deploy.sh

echo "============================================"
echo " 🚀 Deploying All Money-Making Assets"
echo "============================================"
echo ""

# Set paths
TRADING_DIR="$HOME/trading"
INCOME_DIR="$HOME/income"
DEPLOY_DIR="$HOME/deploy_assets"

mkdir -p "$DEPLOY_DIR"

# Copy trading assets
echo "[1/5] Copying trading assets..."
cp "$TRADING_DIR/ftmo_challenge_tracker.html" "$DEPLOY_DIR/"
cp "$TRADING_DIR/sell.html" "$DEPLOY_DIR/index.html"
echo "  ✅ Trading assets ready"

# Copy income/bugflow assets
echo "[2/5] Copying income assets..."
if [ -f "$INCOME_DIR/bugflow_saas_landing.html" ]; then
  cp "$INCOME_DIR/bugflow_saas_landing.html" "$DEPLOY_DIR/bugflow.html"
  echo "  ✅ BugFlow landing page ready"
fi
echo "  ✅ Income assets ready"

# Create a simple redirect
echo "[3/5] Creating redirect..."
cat > "$DEPLOY_DIR/_redirects" << 'EOF'
/*    /index.html   200
EOF
echo "  ✅ Redirects ready"

# Check if Netlify CLI is available
echo "[4/5] Checking deployment options..."
NETLIFY_READY=false

if command -v netlify &> /dev/null; then
  echo "  ✅ Netlify CLI found"
  NETLIFY_READY=true
else
  echo "  ⚠️ Netlify CLI not installed"
  echo "  To install: npm install -g netlify-cli"
fi

# Summary
echo ""
echo "[5/5] Deployment Summary"
echo "============================================"
echo ""
echo "📁 All assets ready in: $DEPLOY_DIR"
echo ""
echo "🌐 Option 1: Netlify (Drag & Drop)"
echo "   1. Go to https://app.netlify.com"
echo "   2. Drag the '$DEPLOY_DIR' folder onto the page"
echo "   3. Your site is live in 30 seconds"
echo "   4. Set custom domain or use netlify.app subdomain"
echo ""
echo "🌐 Option 2: GitHub Pages (5 min)"
echo "   1. Create repo: ftmo-tracker"
echo "   2. git init && git add . && git commit -m 'initial'"
echo "   3. git remote add origin <your-repo-url>"
echo "   4. git push -u origin main"
echo "   5. Enable GitHub Pages in repo settings"
echo ""
echo "🌐 Option 3: Cloudflare Pages (Fastest)"
echo "   1. Go to https://dash.cloudflare.com"
echo "   2. Workers & Pages → Create → Upload"
echo "   3. Upload $DEPLOY_DIR contents"
echo ""
echo "💰 After deploying:"
echo "   1. Set up Gumroad: https://gumroad.com"
echo "   2. Create product 'FTMO Challenge Tracker Pro'"
echo "   3. Set price to \$19.99/month"
echo "   4. Paste Gumroad link into sell.html buy button"
echo "   5. Share on Reddit (r/FTMO, r/DayTrading)"
echo ""
echo "📣 Quick promo links:"
echo "   Reddit: https://reddit.com/r/FTMO"
echo "   Reddit: https://reddit.com/r/DayTrading"
echo "   Discord: search disboard.org for 'FTMO' servers"
echo ""
echo "============================================"
echo " ✅ Deploy script complete!"
echo "============================================"
