# Aprendi

("I learned" — Portuguese.) The NAS-side orchestrator for this project.
Named for the project's own learning priority (see `prompt.md`), not just
its technical function — this component's job goes beyond waking the
desktop: it will check desktop state, trigger and monitor inference jobs,
handle retries/notifications, and eventually run the source-fetching
pipeline for the Weekly Learning Brief. See `docs/phases/phase-1-foundation.md`
and `docs/decisions/0002-compute-orchestration-model.md` for the full
design this will grow into.

Currently just a heartbeat loop (phase 1 skeleton), proving the container
runs reliably on the NAS within its memory constraints.

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
cd aprendi
docker buildx build --platform linux/amd64 \
  -t ghcr.io/breadandwine/aprendi:latest \
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
Packages → `aprendi` → Package settings → Change visibility) so the NAS
can pull it without needing registry credentials configured in UGOS. The
image contains no secrets — only the orchestrator code — so public
visibility is fine.

## Deploying on the NAS

1. Open UGOS's Docker app → Compose / Project import.
2. Paste the contents of `docker-compose.yml` from this folder.
3. Deploy.
4. Verify the container is running and logging:
   - `docker logs aprendi` should show a "Heartbeat: ..." line roughly
     every 60 seconds (configurable via `HEARTBEAT_INTERVAL_SECONDS`).
   - Logs are also written to `/volume1/docker/aprendi/logs/orchestrator.log`
     on the NAS's filesystem (matching the existing `/volume1/docker/<app>`
     convention used for other containers on this NAS), so they persist
     across container restarts and can be checked without going through
     Docker at all.

## Resource constraints

The NAS has very little free memory at idle (observed ~300MB free out of
7.5GB, with swap already in active use — see ADR-0001 implementation
notes). `docker-compose.yml` sets a hard `mem_limit: 128m` on this
container so it cannot make that worse; if ever exceeded, Docker restarts
the container rather than let it degrade the rest of the NAS.


## Email Credentials (.env)

Copy `.env.example` to `.env` in this folder and fill in real values.
`.env` is gitignored and must never be committed.

`docker-compose.yml` references these via `${GMAIL_ADDRESS}` etc., which
standard `docker compose` substitutes automatically from a `.env` file in
the same directory when run from the command line.

**If deploying via UGOS's Docker Compose paste-in UI**: it's not
confirmed whether UGOS's backend performs the same automatic `.env`
substitution when a compose file is pasted directly (rather than run from
a real folder via CLI). If the container fails to start or logs show
missing/empty values for `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD`, or
`BRIEF_RECIPIENT_EMAIL`, check whether UGOS's UI has its own separate
"Environment Variables" input field — if so, enter the values there
directly instead of relying on `.env` substitution, and remove the
`env_file`/`${...}` reliance for this deployment.


## Desktop Shutdown Key (one-time setup)

After a scheduled job confirms the desktop is ready (see scheduler.py),
Aprendi shuts it back down via SSH, since no real job pipeline exists yet
to run first. This requires a dedicated SSH keypair — not your personal
key — authorized on the desktop.

On the NAS, generate a keypair and place it where the compose file
expects it:

```bash
mkdir -p /volume1/docker/aprendi/ssh
ssh-keygen -t ed25519 -f /volume1/docker/aprendi/ssh/aprendi_id_ed25519 -N "" -C "aprendi@nas"
```

(`-N ""` means no passphrase — required since this key needs to be used
unattended by a scheduled job with no human to type a passphrase.)

Copy the **public** key's contents (`aprendi_id_ed25519.pub`) to the
desktop's `~/.ssh/authorized_keys` (append, don't overwrite, if other
keys are already authorized there):

```bash
cat /volume1/docker/aprendi/ssh/aprendi_id_ed25519.pub
# paste the output into ~/.ssh/authorized_keys on the desktop
```

The private key directory is mounted read-only into the container at
`/app/ssh` (see `docker-compose.yml`). Ensure the private key file is
readable by UID 1000 (Aprendi's container user) — same ACL/permission
considerations as the log volume; see `docs/decisions/0002-compute-orchestration-model.md`
implementation notes if this needs troubleshooting.

The desktop's sudoers already allows passwordless `shutdown` for this
user (`/etc/sudoers.d/marcelo-wol`, set up during original Wake-on-LAN
configuration), so no further desktop-side changes are needed for the
shutdown command itself to work.
