# Deploy Trail Log on Netlify

This is a free static app. Trails and photos are saved in browser storage on the phone that uses the journal. They do not sync to another phone or browser, so use the same browser and do not clear its website data.

## Publish today

1. Sign in to [Netlify](https://www.netlify.com/) with GitHub.
2. Select **Add new site**, then **Import an existing project**.
3. Choose the `erionas-hiking-journal` repository.
4. Netlify reads `netlify.toml`. Confirm the base directory is `frontend`, the build command is `npm run build`, and the publish directory is `dist`.
5. Select **Deploy site**. Netlify gives you a free HTTPS address.
6. Open that address in Safari on the phone, then use Safari's Share menu to add it to the Home Screen.

## Updating the app

Push a commit to GitHub. Netlify automatically rebuilds and publishes the update.