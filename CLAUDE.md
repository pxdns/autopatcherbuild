# Working on the autopatcher build repo (pxdns/autopatcherbuild)

Public repo for the website and the build workflow. The patcher source is in the private repo `pxdns/patcher`.

## Rules
- Never commit a token, a Minecraft/Mojang jar, decompiled game code, or a built client. Releases hold the patcher package only.
- The token (`PATCHER_TOKEN`) lives only in Actions secrets. Do not echo it, pass it on a command line, or write it to a file.
- Do not add workflow triggers other than `workflow_dispatch`. In particular never `pull_request_target`, and never run untrusted code with secrets.
- Large files go in Releases, not commits (GitHub rejects files over 100 MB).
- Ask the user before big features. Report results honestly: say what was and was not run.
- Commit trailers: `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>` and the `Claude-Session:` link.

## State
- The workflow has not run yet (needs the secret). See README for what is expected to need adjusting.
