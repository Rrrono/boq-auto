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
- Firebase Auth sign-in page and frontend route gating groundwork

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

If you also want local sign-in, add your Firebase web app values into `.env.local`:

```powershell
NEXT_PUBLIC_FIREBASE_API_KEY=
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=
NEXT_PUBLIC_FIREBASE_PROJECT_ID=
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=
NEXT_PUBLIC_FIREBASE_APP_ID=
```

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
- hosted auth is enabled by explicitly exposing the Firebase web app values through `NEXT_PUBLIC_FIREBASE_*` variables in `apphosting.yaml`

## Firebase Auth

The current auth layer is Phase 1 groundwork:

- hosted and local frontend sign-in via Firebase Auth
- `/login` page
- client-side route gating for the web workspace
- sign-out from the sidebar

Before login works, enable a provider in Firebase Console:

1. Open Firebase Console
2. Go to `Authentication`
3. Open `Sign-in method`
4. Enable `Email/Password`
5. Create at least one internal user

Current limitation:

- frontend access is gated, but backend API token verification is not enforced yet
- the next hardening step is passing Firebase ID tokens to the API and verifying them server-side

Typical setup flow:

```bash
firebase init apphosting
```

Choose:

- the existing Firebase project
- the GitHub repository
- app root directory: `web`
- live branch: `feature/ai-config-ui` for now, or `main` once merged
