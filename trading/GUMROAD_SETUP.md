# 🚀 Gumroad Setup Guide — FTMO Challenge Tracker Pro

## Set up your product in 5 minutes

---

### Step 1: Create a Gumroad Account

1. Go to **[gumroad.com](https://gumroad.com)** and sign up (free)
2. Confirm your email

### Step 2: Create the "FTMO Challenge Tracker Pro" Product

1. Click **"New Product"**
2. Set the following:

| Field | Value |
|-------|-------|
| **Name** | FTMO Challenge Tracker Pro |
| **Description** | Cloud-synced FTMO challenge tracking with unlimited accounts, PDF reports, and email alerts. |
| **Price** | $19.99 |
| **Recurring** | ✅ Monthly subscription |
| **Product URL** | `ftmo-tracker-pro` (or whatever you want) |
| **Thumbnail** | Upload a screenshot of the tracker dashboard |

3. Click **"Create Product"**

### Step 3: Get Your Buy Link

After creating the product, you'll get a URL like:
```
https://gumroad.com/l/ftmo-tracker-pro
```

### Step 4: Update the Buy Buttons

Copy the product **slug** from your Gumroad product URL (the part after `/l/`) and replace `YOUR_PRODUCT_SLUG` in these files:

**File 1: `~/trading/ftmo_challenge_tracker.html`**
- Find `YOUR_PRODUCT_SLUG` and replace with your actual slug (e.g., `ftmo-tracker-pro`)
- The full link will become `https://gumroad.com/l/ftmo-tracker-pro`

**File 2: `~/trading/sell.html`**
- Same replacement

**File 3: `~/deploy_assets/ftmo_challenge_tracker.html`** (for deployed site)
- Same replacement after deploying

### Step 5: Test the Purchase Flow

1. Open the buy link in an incognito window
2. Go through the purchase process (test cards: Gumroad provides test mode)
3. Verify you receive the purchase notification email

### Step 6: Start Selling!

Post the Reddit post (see `~/trading/REDDIT_POST.md`) and start getting users.
