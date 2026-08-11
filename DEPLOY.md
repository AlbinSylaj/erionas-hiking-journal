# Deploy Trail Log on GitHub Pages

This is a free static app. Trails and photos are saved in browser storage on the phone that uses the journal. They do not sync to another phone or browser, so use the same browser and do not clear its website data.

## Publish today

1. On GitHub, open the `erionas-hiking-journal` repository and select **Settings**.
2. Under **General**, scroll to **Danger Zone** and change the repository visibility to **Public**. GitHub Pages is free for public repositories.
3. Open **Settings**, then **Pages**.
4. Under **Build and deployment**, select **GitHub Actions** as the source.
5. The deployment starts automatically. When it finishes, the journal will be available at `https://albinsylaj.github.io/erionas-hiking-journal/`.
6. Open that address in Safari on the phone, then use Safari's Share menu to add it to the Home Screen.

## Updating the app

Push a commit to GitHub. The Pages workflow automatically rebuilds and publishes the update.