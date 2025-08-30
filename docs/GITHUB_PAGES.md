# Host Privacy Policy via GitHub Pages

Use GitHub Pages to publish a public HTTPS link for your privacy policy, without relying on your server.

## Setup (once)
- In your GitHub repo: Settings → Pages.
- Source: Deploy from a branch.
- Branch: `main`, Folder: `/docs`.
- Save. GitHub will publish at `https://<your-username>.github.io/<repo>/`.

## Files
- `docs/index.html`: simple landing page (added).
- `docs/privacy_policy.html`: full policy (already added). Public URL becomes:
  - `https://<your-username>.github.io/<repo>/privacy_policy.html`

## Play Console
- Use the above privacy policy URL in the Store listing.
- Keep policy in sync with repository updates.

## Custom Domain (optional)
- Add a `CNAME` file under `/docs` with your domain.
- Point DNS (CNAME) to `<your-username>.github.io`.
