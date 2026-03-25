# BOQ AUTO Web

This is the internal-first Next.js frontend for the BOQ AUTO cloud platform.

Current Phase 1 features:

- dashboard with job activity
- job creation
- BOQ upload against a job
- pricing run trigger
- latest pricing summary and artifact review
- live price-check page backed by `/price-check`
- live knowledge review page backed by `/knowledge/candidates`

## Local Run

1. Install packages:

```powershell
cd web
npm install
```

2. Create a local environment file:

```powershell
Copy-Item .env.local.example .env.local
```

3. Point the frontend at either:

- the local API: `http://127.0.0.1:8080`
- or the live Cloud Run API URL

4. Start the app:

```powershell
npm run dev
```

## Firebase App Hosting

This app is intended to be deployed with Firebase App Hosting using `web/` as the app root.

Important notes:

- `apphosting.yaml` lives in this directory because Firebase App Hosting expects configuration in the app root
- `BOQ_AUTO_API_BASE_URL` is configured there for hosted runtime access to the BOQ AUTO API
- when creating the App Hosting backend, set the app root directory to `web`

Typical setup flow:

```bash
firebase init apphosting
```

Choose:

- the existing Firebase project
- the GitHub repository
- app root directory: `web`
- live branch: `feature/ai-config-ui` for now, or `main` once merged
