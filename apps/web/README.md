# ArchPilot AI Web

This folder contains a minimal Next.js frontend for the ArchPilot AI project.  It provides three pages:

* **Chat page** (`/`): ask questions against the knowledge base and view responses with citations.
* **Upload page** (`/upload`): upload documents for ingestion.
* **History page** (`/history`): list past conversations (future work).

The frontend uses the `NEXT_PUBLIC_API_URL` environment variable to call the API.  When running via Docker Compose the API is available at `http://localhost:8000`.

To develop the frontend locally:

```bash
cd apps/web
npm install
npm run dev
```

Then open [http://localhost:3000](http://localhost:3000).