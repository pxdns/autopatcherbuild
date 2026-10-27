# Autopatcher build (`pxdns/autopatcherbuild`)

Pick a Minecraft version, download its patcher, run it with **your own** official client jar.

- **What this repo is:** the public side. It holds the build workflow, a small website (`site/`) and the scripts. It holds no secrets and no Minecraft files.
- **What the build does:** [`build-patcher.yml`](.github/workflows/build-patcher.yml) checks out the private patcher repo (`pxdns/eaglercraft-26.2`) with a token kept in an Actions secret, builds that version's patcher package (a single `Setup.jar`), checks that no Minecraft jar is inside it, and publishes it as a **GitHub Release** here.
- **What it does not do:** it never stores or publishes Mojang's client jar or a built client. The official jar is downloaded on the runner only to verify the target descriptor, and is thrown away with the runner.

## Status

| Version | State |
| --- | --- |
| 26.2 | first target; expected to build once `PATCHER_TOKEN` is set |
| 26.3 | descriptor is still a placeholder in the private repo (base patches not re-pointed yet) |
| 1.16.5 | in progress in the private repo |
| 1.14, 1.12 | planned; need a base port first |

**Not yet run.** The workflow was written against the private repo's scripts (`build.sh`, `make-portable.sh`, `make-single-file.sh`) but has never executed, because it needs the secret. Expect the first run to point out something that needs adjusting; each step prints what failed.

## Setup (once)

See [docs/SETUP.md](docs/SETUP.md): create a read-only token for the private repo, add it as the `PATCHER_TOKEN` secret, and turn on GitHub Pages for the `site/` folder.

## Using a release

1. Download `Eaglercraft-<version>-Setup.jar` from the [Releases](../../releases) page (or the site).
2. Run it with Java 17 or newer: `java -jar Eaglercraft-<version>-Setup.jar`.
3. Choose your own official client jar for that version, then build.

## Rules for this repo

- Never commit a token, a Minecraft jar, or a build of the game.
- Builds start only by hand (`workflow_dispatch`). Do not add triggers that run on pull requests, because a pull request's code could then reach the secret.
- Large files go in Releases, not in commits.

Not affiliated with Mojang or Microsoft. Credit: the "download the patcher, run it with your own jar" approach follows the Eaglercraft 26.2 patcher by matej.
