# Tickets — Special-Sprinkle-Sauce

This repo uses a **file-based ticketing system** managed by the `ticketing` Claude Code plugin. Every ticket is a markdown file with YAML frontmatter. No database, no external service — everything lives in git alongside the code.

**Ticket ID prefix:** `SSS` (e.g., `SSS-T001`, `SSS-T002`, ...)

---

## Directory layout

```
docs/
  tickets/
    .config.json        # prefix + next_id (do not hand-edit unless needed)
    README.md           # this file
    INDEX.md            # auto-generated list of all tickets
    open/               # not yet started
    in-progress/        # actively being worked on
    done/               # completed
    .drafts/            # gitignored scratch space (optional)
  decisions/            # Architecture Decision Records (ADRs)
    INDEX.md
    0001-*.md
  lessons/              # Post-mortems / lessons learned
    INDEX.md
    YYYY-MM-DD-*.md
```

---

## The 6 skills

| Skill | What it does |
|-------|--------------|
| `/ticketing:init` | One-time setup: creates directories, config, and index files. |
| `/ticketing:new "Title"` | Creates a new ticket in `open/` with an auto-incremented ID. |
| `/ticketing:move <ID> <state>` | Moves a ticket between `open`, `in-progress`, and `done`. |
| `/ticketing:list [state]` | Regenerates `INDEX.md` and prints a summary. |
| `/ticketing:adr "Title"` | Creates a new Architecture Decision Record in `docs/decisions/`. |
| `/ticketing:lesson "Title"` | Creates a new post-mortem / lessons-learned doc in `docs/lessons/`. |

### Examples

```bash
# Create a ticket
/ticketing:new "Add MFA to login flow"
# → docs/tickets/open/SSS-T001-add-mfa-to-login-flow.md

# Start work
/ticketing:move SSS-T001 in-progress

# Finish
/ticketing:move SSS-T001 done

# See everything
/ticketing:list

# Log a decision
/ticketing:adr "Use Postgres for primary store"

# Log a post-mortem
/ticketing:lesson "Rate-limit outage 2026-04-10"
```

---

## Workflow

```
open  ──/ticketing:move <ID> in-progress──▶  in-progress  ──/ticketing:move <ID> done──▶  done
```

- **One ticket per file.** Tickets are self-contained — the frontmatter has metadata, the body has the narrative.
- **Status is the frontmatter `status` field.** The directory (`open/`, `in-progress/`, `done/`) mirrors it — the `move` skill keeps both in sync.
- **IDs are immutable.** Once a ticket is created as `SSS-T042`, it keeps that ID forever, even across state changes.

---

## Frontmatter reference

Every ticket starts with a YAML block:

```yaml
---
id: SSS-T001                     # immutable, auto-generated
title: Short human title          # required
status: open                      # open | in-progress | done
priority: medium                  # low | medium | high | critical
type: feature                     # feature | bug | chore | research | refactor
owner: joe                        # who's responsible
created: 2026-04-10               # auto-set on creation
updated: 2026-04-10               # auto-bumped on move
closed: 2026-04-20                # auto-set on move → done
related-pr: https://...           # optional
related-tickets: [SSS-T005]       # optional
---
```

Edit freely after creation — add custom fields, adjust priority, link related tickets. The `list` skill only reads the fields it knows about and ignores the rest.

---

## Conventions

- **Filename:** `<ID>-<slug>.md` — e.g., `SSS-T001-add-mfa-to-login.md`.
- **Slug:** lowercase, hyphenated, 40 chars max.
- **ID format:** `SSS-T<3-digit-zero-padded>` for tickets, `<4-digit>-<slug>` for ADRs, `YYYY-MM-DD-<slug>` for lessons.
- **INDEX.md files are auto-generated.** Don't hand-edit — re-run `/ticketing:list` (or the corresponding skill) to refresh.
- **Commit tickets with the code change** that addresses them. A done ticket should point to the PR that closed it via `related-pr`.

---

## FAQ

**Q: Can I rename a ticket after creating it?**
Yes — edit the `title` field and the filename together, then run `/ticketing:list` to refresh INDEX.md. The ID stays the same.

**Q: What if two of us create a ticket at the same time?**
The `next_id` in `.config.json` is not lock-protected. In practice, just resolve the merge conflict by bumping the second ticket's ID and renaming the file. Rare enough not to worry about.

**Q: How do I reopen a done ticket?**
`/ticketing:move <ID> open` (or `in-progress`). It moves the file and updates the frontmatter. The `closed` date stays as a historical record.
