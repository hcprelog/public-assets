# Gmail API Setup — H&C Precise Logistics Vendor Outreach Automation

One-time setup to allow GitHub Actions to send from dennis@hcprelog.com.
Takes ~15 minutes. Do this from a desktop browser.

---

## STEP 1: Create Google Cloud Project + Enable Gmail API

1. Go to console.cloud.google.com → New Project → Name: "HC Outreach Automation"
2. APIs & Services → Library → search "Gmail API" → Enable
3. APIs & Services → OAuth consent screen:
   - User type: External
   - App name: HC Outreach Automation
   - User support email: hcprelog@gmail.com
   - Developer email: hcprelog@gmail.com
   - Save → Add scopes: `https://www.googleapis.com/auth/gmail.send` + `https://www.googleapis.com/auth/gmail.readonly`
   - Add test user: hcprelog@gmail.com
   - Save

---

## STEP 2: Create OAuth 2.0 Credentials

1. APIs & Services → Credentials → Create Credentials → OAuth client ID
2. Application type: Desktop app
3. Name: HC Outreach Bot
4. Download JSON → Save as `client_secret.json` (keep local, never commit)
5. Note your Client ID and Client Secret

---

## STEP 3: Generate Refresh Token (one-time, in terminal)

```bash
pip install google-auth-oauthlib

python3 -c "
from google_auth_oauthlib.flow import InstalledAppFlow
flow = InstalledAppFlow.from_client_secrets_file(
    'client_secret.json',
    scopes=['https://www.googleapis.com/auth/gmail.send',
            'https://www.googleapis.com/auth/gmail.readonly']
)
creds = flow.run_local_server(port=0)
print('REFRESH TOKEN:', creds.refresh_token)
"
```

- Browser opens → log in as hcprelog@gmail.com → Allow
- Copy the REFRESH TOKEN printed in terminal

---

## STEP 4: Add GitHub Secrets

Go to: github.com/hcprelog/public-assets → Settings → Secrets and variables → Actions → New repository secret

Add these 3 secrets:

| Secret Name          | Value                        |
|----------------------|------------------------------|
| `GMAIL_CLIENT_ID`    | From Step 2 (ends in .apps.googleusercontent.com) |
| `GMAIL_CLIENT_SECRET`| From Step 2                  |
| `GMAIL_REFRESH_TOKEN`| From Step 3                  |

---

## STEP 5: Test the workflow

1. GitHub → Actions → "Vendor Outreach & Reply Monitor" → Run workflow
2. Select mode: `outreach` + check "Dry run" → Run
3. Check the run log — should show all COLD/DRAFTED candidates without sending
4. If good: run again with dry_run = false to send live emails

---

## How the automation works (ongoing)

| Time | Action |
|---|---|
| Weekdays 9 AM ET | Outreach run: finds COLD candidates → sends emails → updates vendor files → commits |
| Weekdays 5 PM ET | Monitor run: checks Gmail for replies → classifies response → updates vendor files → commits |
| Any time | Manual dispatch from GitHub Actions tab — choose mode + dry_run option |

## Adding new vendor candidates

1. Add company to the relevant `/govcon/vendors/naics-[code]-subs.md` file
2. Set Status = `COLD — not yet contacted`
3. Include Email field (required for automation)
4. Commit and push → next 9 AM ET run will send outreach automatically

## What triggers a reply update

When a vendor replies to any outreach email, the 5 PM monitor will:
- Detect the reply in the Gmail thread
- Classify it: INTERESTED / NOT_INTERESTED / FOLLOW_UP_NEEDED / REVIEW_NEEDED
- Update the vendor file status with the classification
- Log the entry in /automation/logs/VENDOR_OUTREACH_LOG.md
- Commit the change to the repo

Interested vendors → check your Gmail + follow up with a call (use SOP Step 6 script)
