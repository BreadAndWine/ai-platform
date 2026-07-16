# Weekly Learning Brief — v1 Source List

This is the curated seed list for the Weekly Learning Brief (see ADR-0003).
It is a human-curated starting point, not an exhaustive or permanent list.
Sources can be added, removed, or reweighted over time — update this file
when that happens, since it's the source of truth for the fetcher config.

Tiering reflects trust/priority, not necessarily fetch frequency:

- **Tier 1**: primary sources (labs, official docs). Prefer these over
  secondary coverage of the same news.
- **Tier 2**: high-signal independent writers and company engineering blogs.
  Good for depth and practitioner experience.
- **Tier 3**: community discussion (Reddit). Use for discovery and
  real-world pitfalls, not as a citable source of truth. Treat as noisier
  and lower-confidence input to curation, not equal-weight with Tier 1/2.

Feed URLs marked `(verified)` were fetched directly and confirmed to return
valid feed content as of 2026-07-16. Feed URLs marked `(unverified)` are the
conventional/likely path but were not confirmed directly (either fetch
tooling rejected the content-type, or no direct feed was found) — check
these when building the actual fetcher.

## Tier 1: Labs & Official Announcements

| Source | Feed / URL | Status |
|---|---|---|
| OpenAI News | https://openai.com/news/rss.xml | verified |
| Anthropic News | https://www.anthropic.com/news | no RSS found; page-scrape or check periodically |
| Google DeepMind Blog | https://deepmind.google/discover/blog/ | no RSS found; page-scrape |
| Google AI Blog | https://blog.google/technology/ai/rss/ | unverified |
| Meta AI Blog | https://ai.meta.com/blog/ | no RSS found; page-scrape |
| Mistral AI News | https://mistral.ai/news | no RSS found; page-scrape |
| Hugging Face Blog | https://huggingface.co/blog/feed.xml | unverified (valid feed, tool rejected content-type) |

## Tier 1: Official Documentation (pull on change, not a feed)

These don't get "fetched weekly" the way blogs do — track release notes /
changelogs specifically, not the whole doc site.

| Source | Docs Root | Notes |
|---|---|---|
| Model Context Protocol (MCP) | https://modelcontextprotocol.io/ | check spec changelog |
| Docker | https://docs.docker.com/ | check release notes |
| Kubernetes | https://kubernetes.io/docs/ | check release notes |
| AWS | https://docs.aws.amazon.com/ | check "What's New" feed: https://aws.amazon.com/about-aws/whats-new/recent/feed/ (unverified) |
| Home Assistant | https://www.home-assistant.io/docs/ | release notes: https://www.home-assistant.io/blog/ |
| Ollama | https://github.com/ollama/ollama/releases | releases as changelog |

## Tier 2: Independent AI Engineering Writers

| Source | Feed / URL | Status |
|---|---|---|
| Simon Willison | https://simonwillison.net/atom/everything/ | verified |
| Lilian Weng (Lil'Log) | https://lilianweng.github.io/index.xml | verified |
| Sebastian Raschka | https://sebastianraschka.com/rss_feed.xml | verified |
| Hamel Husain | https://hamel.dev/index.xml | verified |
| Eugene Yan | https://eugeneyan.com/rss/ | unverified (index.xml returned 404, try /rss/ or check site) |

## Tier 2: Engineering Blogs

| Source | Feed / URL | Status |
|---|---|---|
| GitHub Engineering | https://github.blog/feed/ | unverified (valid feed, tool rejected content-type) |
| Netflix Tech Blog | https://netflixtechblog.com/feed | unverified |
| Airbnb Engineering | https://medium.com/airbnb-engineering/feed | unverified |
| Stripe Engineering | https://stripe.com/blog/feed.rss | unverified (valid feed, tool rejected content-type) |
| Cloudflare Blog | https://blog.cloudflare.com/rss/ | unverified (valid feed, tool rejected content-type) |
| Meta Engineering | https://engineering.fb.com/feed/ | unverified |
| Google Cloud Blog | https://cloud.google.com/blog/rss/ | unverified |
| Microsoft Engineering | https://devblogs.microsoft.com/feed/ | unverified |
| Uber Engineering | https://www.uber.com/blog/engineering/rss/ | unverified |

## Tier 3: Community (discovery only, not authoritative)

| Source | Feed / URL | Notes |
|---|---|---|
| r/LocalLLaMA | https://www.reddit.com/r/LocalLLaMA/.rss | use for tool discovery, pitfalls |
| r/selfhosted | https://www.reddit.com/r/selfhosted/.rss | |
| r/HomeAssistant | https://www.reddit.com/r/homeassistant/.rss | |
| r/MachineLearning | https://www.reddit.com/r/MachineLearning/.rss | |
| r/homelab | https://www.reddit.com/r/homelab/.rss | |

## Open Items

- Several feed URLs above are marked unverified — either the fetch tool
  used to build this list rejected the XML content-type (likely still
  valid feeds; a real RSS parser should handle them fine), or no direct
  feed could be found and the source will need periodic page-scraping
  instead of feed polling. Verify these directly once the NAS-side fetcher
  is being built (a normal RSS library, e.g. Python's `feedparser`, should
  handle content-types this fetch tool couldn't).
- Labs without RSS (Anthropic, DeepMind, Meta AI, Mistral) will need either
  periodic scraping or a third-party feed bridge (e.g. RSSHub) — decide
  this during fetcher implementation, not now.
- r/LocalLLaMAAI mentioned as "if active" — could not confirm this
  subreddit exists/is active; using r/LocalLLaMA as the primary ML-hardware
  community source instead. Flag if you meant a different subreddit.
