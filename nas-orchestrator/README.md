# NAS Orchestrator

Phase 1 skeleton for the NAS-side orchestrator (see
`docs/phases/phase-1-foundation.md` and `docs/decisions/0002-compute-orchestration-model.md`).
Currently just a heartbeat loop, proving the container runs reliably on
the NAS within its memory constraints. Future phases will extend
`app/main.py` with the real desktop state check, Wake-on-LAN, and source
fetching logic.

## Why a pre-built image, not a build context

The NAS runs UGOS (UGREEN's OS), and its Docker app's Compose import only
supports pulling a pre-built `image:`, not a local `build:` context. So
instead of building on the NAS, the image is built on a dev machine and
pushed to GitHub Container Registry (`ghcr.io`), which the NAS then pulls.

GHCR was chosen over Docker Hub because the code already lives on GitHub,
avoiding a second registry account, and it's free for public images (no
budget impact, per ADR-0001's no-cloud-spend constraint — this is a
registry for a public artifact, not a paid cloud service).

## Building and pushing a new image

The NAS's CPU (Intel N100) is `linux/amd64`. If building from an Apple
Silicon Mac (arm64), you must explicitly cross-build for `linux/amd64` —
otherwise the image won't run on the NAS.

```bash
cd nas-orchestrator
docker buildx build --platform linux/amd64 \
  -t ghcr.io/breadandwine/ai-platform-orchestrator:latest \
  --push .
```

This requires being logged in to `ghcr.io` first:

```bash
echo "<YOUR_GITHUB_PAT_WITH_write:packages_SCOPE>" | \
  docker login ghcr.io -u breadandwine --password-stdin
```

Never commit the token. Run the login command directly in your own shell,
not saved to any file in this repo.

## Package visibility

The GHCR package must be set to **Public** (via GitHub → your profile →
Packages → `ai-platform-orchestrator` → Package settings → Change
visibility) so the NAS can pull it without needing registry credentials
configured in UGOS. The image contains no secrets — only the orchestrator
code — so public visibility is fine.

## Deploying on the NAS

1. Open UGOS's Docker app → Compose / Project import.
2. Paste the contents of `docker-compose.yml` from this folder.
3. Deploy.
4. Verify the container is running and logging:
   - `docker logs ai-platform-orchestrator` should show a "Heartbeat: ..."
     line roughly every 60 seconds (configurable via
     `HEARTBEAT_INTERVAL_SECONDS`).
   - Logs are also written to
     `/volume1/docker/ai-platform-orchestrator/logs/orchestrator.log` on
     the NAS's filesystem (matching the existing `/volume1/docker/<app>`
     convention used for other containers on this NAS), so they persist
     across container restarts and can be checked without going through
     Docker at all.

## Resource constraints

The NAS has very little free memory at idle (observed ~300MB free out of
7.5GB, with swap already in active use — see ADR-0001 implementation
notes). `docker-compose.yml` sets a hard `mem_limit: 128m` on this
container so it cannot make that worse; if ever exceeded, Docker restarts
the container rather than let it degrade the rest of the NAS.
