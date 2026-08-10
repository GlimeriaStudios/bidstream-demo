# Bidstream

AI-powered tender intelligence — *know which contracts you can actually win.*

Bidstream reads the whole public and private tender market and hands a company a short, ranked list of contracts matched to what it actually does, with the reasoning shown. This repository holds the brand system, go-to-market materials, marketing assets, and the landing page.

---

## Repository contents

```
.
├── website/          Landing page (deployable via GitHub Pages)
│   ├── index.html                       main site (references office.png)
│   ├── office.png                       hero photo used by index.html
│   └── bidstream-website-standalone.html single self-contained file (image embedded)
│
├── brand/            Brand system
│   └── Bidstream-Brand-Guidelines.html  full visual identity (open in a browser)
│
├── decks/            Presentations (PowerPoint)
│   ├── Bidstream-GTM-Strategy.pptx       18-slide go-to-market strategy
│   ├── Bidstream-Outreach-Slide.pptx     single outreach slide
│   └── Bidstream-Timeline-Slide.pptx     standalone 24-month timeline slide
│
└── assets/           Marketing images
    ├── linkedin/     1200×1200 LinkedIn post graphics
    │   ├── founder-outreach.png
    │   ├── stat-post.png
    │   ├── founding-member-offer.png
    │   └── photo-post.png
    └── photos/
        ├── office-photo.png              real office photograph
        └── office-scene-illustration.png geometric brand illustration
```

## The landing page

The site is a single-page, dependency-free build (plain HTML/CSS/JS — no framework, no build step). Two forms are included as front-end stubs.

**View locally:** open `website/index.html` in any browser (keep `office.png` beside it), or open `website/bidstream-website-standalone.html` on its own.

**Deploy with GitHub Pages:**
1. Push this repository to GitHub.
2. Settings → Pages → Build and deployment → Source: *Deploy from a branch*.
3. Branch: `main`, folder: `/root` (or move `website/`'s contents to the repo root, or `/docs`).
4. Your site goes live at `https://<user>.github.io/<repo>/`.

> Note: the sign-up forms currently show a confirmation message but do **not** capture the email address anywhere. Wire them to a provider (Formspree, Tally, etc.) before collecting real sign-ups.

## Brand system

`brand/Bidstream-Brand-Guidelines.html` is the source of truth for the visual identity:

| Token | Hex | Use |
| --- | --- | --- |
| Indigo Ink | `#0B1020` | Primary text, dark sections |
| Signal Blue | `#3D7BFF` | Primary brand colour, links, actions |
| Win Amber | `#FFB020` | The "win" moment only — used sparingly |
| Flow Teal | `#2DD4BF` | Secondary accent, data highlights |

Typography: **Space Grotesk** (display) · **Inter** (body) · **JetBrains Mono** (data/labels).

## Go-to-market summary

A four-phase, 24-month plan, each phase gated on the previous one producing real evidence:

1. **Prove it works** (months 0–6) — founding-member offer: free access for real feedback and testimonials.
2. **Sell the proof** (months 6–9) — raise price using the results; proof-led creative.
3. **Focus on the best fits** (months 9–15) — concentrate on the two strongest industries.
4. **Own the space** (months 15–24) — monthly market report, partners, category ownership.

Full detail is in `decks/Bidstream-GTM-Strategy.pptx`.

## License

See [LICENSE](LICENSE). The office photograph in `website/` and `assets/photos/` may be subject to separate licensing — confirm its rights before publishing.
