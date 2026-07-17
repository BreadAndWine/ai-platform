# ADR-0001: Hardware Topology and Constraints

- **ID**: ADR-0001
- **Date**: 2026-07-16
- **Status**: Accepted
- **Review Date**: 2027-01-16 (or sooner if NAS/desktop hardware changes)

## Decision

For the current phase, the platform is built around the hardware that already
exists, with no purchases assumed:

- **NAS (UGREEN DXP2800, Intel N100, 8GB RAM, UGOS + Docker)**: always-on
  orchestration and storage node. It does **not** run meaningful LLM
  inference. It is responsible for scheduling, fetching data, deduplication,
  state/storage, and notification (email).
- **Desktop (Ryzen 5600X + AMD RX 9070 XT)**: on-demand compute node for
  actual LLM inference. Currently Windows-only, gaming rig. Will be
  dual-booted with Linux to support GPU-accelerated inference (ROCm 7.2+,
  which is the first ROCm release with official RDNA4 support, or Vulkan as
  a fallback backend for llama.cpp if ROCm proves unstable).
- **No cloud APIs, no cloud spend.** Everything runs locally, even if that
  means starting with lower-quality output than a cloud LLM would give.

## Context

The project starts from a blank slate. The NAS is a low-power, CPU-only,
RAM-constrained box that runs continuously. The desktop has real GPU compute
but is normally powered off and is the user's primary gaming machine, not a
dedicated server. The user is explicit about not wanting cloud API costs or
dependencies, even at the cost of starting from zero capability.

## Reasoning

A CPU-only 8GB-RAM box cannot run a model capable of producing high-quality
summarization/curation output (the core task of the first application) at
acceptable speed. Realistic local models on the N100 are limited to small
(1-3B parameter) quantized models, which is not enough to make the first
application worth using. The RX 9070 XT is the only hardware capable of
running a 7B-14B class model at usable speed, so it must be part of the
architecture despite being intermittently available.

## Alternatives Considered

- **Use a cloud LLM API for inference**: Rejected. Violates explicit no-cloud,
  no-budget, privacy-first constraints.
- **NAS-only inference with tiny models**: Rejected as the primary strategy.
  Quality would be too low to produce a useful first application, though
  small local models on the NAS may still be used later for cheap/simple
  tasks (e.g. deduplication heuristics, not summarization).
- **Upgrade NAS hardware**: Deferred. No indication yet that this is
  necessary or wanted; revisit if the orchestration workload itself (not
  inference) outgrows the N100/8GB.

## Trade-offs

- Gains real inference quality by using the desktop GPU.
- Costs: added complexity (dual-boot, remote triggering, availability
  detection), and inference is not always available on demand since the
  desktop is not always on or free.

## Consequences

- Desktop dual-boot to Linux is a phase 1 prerequisite task.
- A wake/trigger mechanism (Wake-on-LAN) from NAS to desktop is required.
- A mechanism to avoid degrading the user's gaming experience when the
  desktop is already powered on and in use is required (see ADR-0002).

## Implementation Notes (Dual-Boot)

Completed 2026-07-17.

- **OS**: Ubuntu 26.04 LTS.
- **Target disk**: the existing SATA SSD (2TB, ~700GB+ free at the time),
  not the NVMe drive Windows lives on. This was a deliberate choice made
  after discovering Windows updates can silently overwrite a shared EFI
  System Partition and disable GRUB (a real, recurring issue, not
  theoretical). Installing Linux on a physically separate drive with its
  own ESP avoids this failure mode entirely, since Windows updates cannot
  touch a different drive's ESP.
- **Partition size**: ~160GB (160000 MB) allocated to Linux out of
  ~1.2TB available shrinkable space on the SATA SSD, sized to comfortably
  fit the OS, ROCm runtime, and multiple resident 7B-14B GGUF models
  without needing to manage disk space tightly. Remaining space on that
  drive (existing games/apps) was untouched by the shrink.
- **Boot selection**: motherboard one-time boot menu (not GRUB
  chainloading Windows) is used to choose between the NVMe (Windows) and
  SATA SSD (Ubuntu) at power-on, keeping both boot chains fully
  independent.
- **Security**: login password set on the Ubuntu account, anticipating
  future SSH-based orchestration from the NAS (see ADR-0002).
- NVMe/Windows drive was not touched (no shrink was needed there; it also
  had insufficient free space for this purpose in any case, ~43GB free at
  the time of investigation).
