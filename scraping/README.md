# Scraping Compliance

## Target domains
- https://rekrutacja.p.lodz.pl/
- https://p.lodz.pl/

## Robots.txt summary

### rekrutacja.p.lodz.pl
- **Allowed**: CSS, JS, image assets under `/core/` and `/profiles/`
- **Disallowed**:
  - `/core/`, `/profiles/`, `/modules/`, `/sites/`, `/themes/`
  - `/admin/`, `/search/`, `/node/add/`, `/comment/reply/`
  - `/user/*` (login, register, password, logout)
  - `/media/oembed`, `/*/media/oembed`
  - `/web.config`
  - `README.md` and composer-related files
- **Crawl-delay**: none specified

### p.lodz.pl
- **Allowed**: CSS, JS, image assets under `/core/` and `/profiles/`
- **Disallowed**:
  - `/core/`, `/profiles/`, `/modules/`, `/sites/`, `/themes/`
  - `/admin/`, `/search/`, `/node/add/`, `/comment/reply/`
  - `/user/*` (login, register, password, logout)
  - `/media/oembed`, `/*/media/oembed`
  - `README.md` and composer-related files
- **Crawl-delay**: none specified

## Compliance checklist
- [x] Robots.txt reviewed and saved in `scraping/robots_*.txt`
- [ ] Respect disallowed paths (do not scrape admin, search, user, etc.)
- [ ] Apply polite rate limiting (default: 1 request/second, since no crawl-delay specified)
- [ ] Only scrape public pages relevant to admissions (fees, requirements, accommodation, legal acts, etc.)
- [ ] Log scraping activity in `logs/`
