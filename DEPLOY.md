# Deploy Trail Log on Render

This project is ready to deploy as one Render web service. It serves the React app, Django API, SQLite journal, and uploaded trail photos from the same public URL.

## Publish today

1. Create a private GitHub repository and push this project to it. Do not commit `.env`.
2. Sign in to [Render](https://render.com/) with GitHub.
3. Select **New +**, then **Blueprint**, and choose the repository.
4. Render reads `render.yaml`. Leave the service name as `trail-log` or choose another available name.
5. Enter the existing `SERPAPI_API_KEY` value when Render asks for it. Do not paste it into GitHub or source files.
6. Create the service and wait for the deployment to finish. Render displays an HTTPS URL such as `https://trail-log.onrender.com`.
7. Open that URL on your iPhone. Add it to the Home Screen from Safari's Share menu for an app-like shortcut.

## Persistent data

The blueprint provisions a 1 GB Render disk at `/var/data`. This keeps the SQLite trail journal and uploaded photos after a deploy or restart. Render disks require a paid web-service plan, which is why the blueprint specifies `starter`.

## Updating the app

Push a commit to the connected GitHub repository. Render automatically rebuilds the React frontend, collects Django static assets, migrates the database, and deploys the update.