# Public demonstration

The frontend opens directly on the dashboard. Login and registration are removed.
Catalogue changes, requests and calculations use browser-local demo data.
No authentication endpoint, VITE_API_URL, Render service or credentials are used.

The synthetic catalogue covers metal, slag, gypsum and mineral materials.
Edits are saved under localStorage key qm_public_demo_v1, isolated per browser.
The analyzer uses labeled category rules, without fabricated similarity scores.
External LLM chat is unavailable and is labeled accordingly.

Vercel Root Directory: QaitaMaterial-AI-Redesign/frontend
Build: npm run build. Output Directory: dist.
Existing VITE_API_URL settings are ignored by the demo.
Push to the production branch triggers deployment if Vercel Git auto-deploy is enabled.
Validation: npm run build; npm test.

Backend authentication is unchanged by this update.
