# Backlog / Parked Ideas

Ideas that are worth remembering but not yet scoped into a phase or ADR.
Move an item into a real ADR/phase plan once it's actually being pursued.

## Custom domain + email forwarding (e.g. ForwardEmail)

- **Idea**: once a domain name is purchased (planned anyway, for reverse
  proxying into the NAS), use a service like forwardemail.net to create
  disposable/per-service email aliases (e.g. `someservice@yourdomain.net`)
  that forward to a real inbox. Purpose is signup privacy — avoid handing
  out a personal address to random services — not related to the Weekly
  Learning Brief.
- **Status**: parked. No domain owned yet, and current constraint is no
  budget (a domain is ~$10-15/year). Revisit once a domain is purchased for
  other reasons.
- **Not a replacement for**: the Weekly Learning Brief's email delivery,
  which uses Gmail SMTP per ADR-0003. This is a separate, general-purpose
  utility.
