# Setup

You do these steps once, in the GitHub web interface. They involve a secret, so they are deliberately not scripted.

## 1. A read-only token for the private repo

1. GitHub > Settings > Developer settings > Personal access tokens > **Fine-grained tokens** > Generate new token.
2. **Repository access:** only `pxdns/eaglercraft-26.2`.
3. **Permissions:** Repository permissions > **Contents: Read-only**. Nothing else.
4. Set an expiry (90 days is fine) and copy the token once. Do not paste it into chat, a file or an issue.

A fine-grained token cannot do anything outside that one repo, which limits the damage if it ever leaks. A GitHub App is stricter still, if you want to move to one later.

## 2. Store it as a secret

In `pxdns/autopatcherbuild`: Settings > Secrets and variables > Actions > **New repository secret**. Name: `PATCHER_TOKEN`. Value: the token.

## 3. Put the website online

The page is the single file `site/index.html`. Two easy ways to host it:

- **Website:** served by Vercel from `site/`; there is no GitHub Pages setup.
- **Vercel:** import the repo and set the root directory to `site/`.

The page reads the repo's releases and workflow runs through GitHub's public API from the visitor's browser, so **the repo must be public** for the status line and download buttons to work. It needs no token.

## 4. Run a build

Actions > **Build patcher package** > Run workflow > run it (there is no version choice yet). When it succeeds, a release appears and the site lists it.

## If a run fails

Each step prints its own error. The likely first problems: a missing input file the packaging script expects from the private repo, or the sparse checkout (`src/patcher`) missing a file a script reads from elsewhere in the repo. Send the failing step's log lines (never the token).
