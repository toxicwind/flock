# Triangle Accessibility — SaaS Architecture & Strategy Blueprint
## triangleaccessibility.com — B2B Document Remediation Platform

**Version:** 1.0  
**Date:** 2026-08-08  
**Status:** Research & Architecture Phase  
**Domain:** triangleaccessibility.com (Porkbun)  
**Target:** B2B accessibility remediation (PDF, Word, PowerPoint)  
**Competitive Benchmark:** 247accessibledocuments.com (to exceed significantly)

---

## 1. Executive Summary

This blueprint outlines a **headless WordPress + Next.js SaaS architecture** for Triangle Accessibility — a B2B document accessibility remediation platform serving the Research Triangle, NC area and beyond. The architecture is designed to be **fully LLM-controllable** via REST/GraphQL APIs, uses **zero paid WordPress plugins**, and leverages **open-source GitHub repositories as submodules** for document processing.

### Core Value Proposition
> "Get a quote in 60 seconds. Upload your documents securely. Receive WCAG 2.1 AA / PDF/UA compliant files with full remediation reports — faster, cheaper, and more transparent than any competitor."

### Why This Beats 247accessibledocuments.com
| Feature | 247accessible | Triangle Accessibility |
|---------|--------------|----------------------|
| Quote System | Manual / Email | Instant dynamic calculator |
| File Upload | Basic / Insecure | Encrypted, virus-scanned, audit-logged |
| Processing Transparency | Black box | Real-time pipeline status + AI preflight |
| Client Portal | None | Full dashboard with download history |
| API/Automation | None | Full REST API for enterprise integration |
| Pricing Visibility | Hidden / Opaque | Instant per-page/per-complexity pricing |
| Social Proof | Minimal | Live case studies, LinkedIn integration |

---

## 2. Architecture Philosophy: "Emergent Max Level — Easy for LLM to Control"

The entire stack is designed around **API-first, JSON-native, programmatic control**:

- **WordPress** = Content backend + user management + custom post types (orders, quotes, files)
- **Next.js Frontend** = SaaS application layer (client portal, quote calculator, file upload)
- **Python Microservices** = Document processing (submoduled GitHub repos)
- **Everything exposed via REST/GraphQL** — no click-ops, no GUI-only workflows

### Design Principles
1. **No Paid Plugins** — All WordPress functionality via custom plugins or open-source MIT/GPL tools
2. **GitHub as Source of Truth** — All processing engines are GitHub submodules, version-controlled
3. **LLM-Native APIs** — Every endpoint returns clean JSON, accepts JSON, documented via OpenAPI
4. **B2B-First** — Multi-tenancy, team roles, SAML SSO ready, audit logs
5. **Security-First** — End-to-end encryption, zero-trust file handling, SOC 2 alignment

---

## 3. Technical Stack

### 3.1 Frontend Layer (Next.js 16 + App Router)
**Recommended Starter:** `ixartz/SaaS-Boilerplate` (MIT License, 12.9k stars)
- Multi-tenancy + RBAC out of the box
- Clerk authentication (free tier: 10k MAU) or self-hosted Better Auth
- Stripe subscriptions + usage-based billing
- Shadcn UI + Tailwind CSS v4
- TypeScript strict mode
- Sentry monitoring + Vitest testing

**Alternative (Minimal):** `nextjs/saas-starter` (Official Vercel, MIT)
- Auth.js v5 + Drizzle ORM + Postgres
- Stripe webhooks + customer portal
- Best for learning/reference architecture

**Why Next.js over WordPress Theme:**
- Superior performance (Core Web Vitals)
- True SaaS app experience (dashboard, real-time updates)
- Omni-channel ready (can spawn mobile app later)
- Complete separation of concerns

### 3.2 WordPress Backend (Headless CMS + API Gateway)
**Role:** Content management, user metadata, order storage, file metadata, webhook orchestration

**Required Plugins (All Free/Open Source):**
| Plugin | Purpose | License |
|--------|---------|---------|
| **WPGraphQL** | GraphQL API layer (canonical, well-maintained) | GPL v2 |
| **Advanced Custom Fields (Free)** | Custom fields for quotes, orders, files | GPL |
| **Custom Post Type UI** | Register `remediation_order`, `quote_request`, `client_file` | GPL |
| **WP REST API (Core)** | Native REST endpoints for media/users | GPL |
| **JWT Authentication for WP REST API** | Stateless auth for API clients | MIT |
| **WP Offload Media Lite** | S3/R2 integration for file storage | GPL |
| **WordPress Connectors (Core 7.0+)** | AI provider integration (Claude, GPT, Gemini) | GPL |

**Custom Plugin Development (You Build These):**
1. `triangle-accessibility-api` — Custom REST endpoints for:
   - `/wp-json/triangle/v1/quote` — POST quote calculation
   - `/wp-json/triangle/v1/upload` — Secure file upload (returns pre-signed URL)
   - `/wp-json/triangle/v1/status/{order_id}` — Pipeline status
   - `/wp-json/triangle/v1/download/{file_id}` — Secure download with audit
   - `/wp-json/triangle/v1/webhook/github` — GitHub PAT-based submodule sync

2. `triangle-accessibility-remediation` — Integration layer for Python microservices

### 3.3 Database Layer
- **Primary:** PostgreSQL (via Supabase or Neon — both have generous free tiers)
- **WordPress:** MySQL (host-provided or PlanetScale)
- **Cache:** Redis (Upstash — free tier: 10k commands/day)
- **Search:** Meilisearch (open source, self-hostable) or Algolia (free tier: 10k records)

### 3.4 File Storage & Security
**Primary:** AWS S3 + CloudFront OR Cloudflare R2 (both have free tiers)
- **Upload:** Pre-signed URL flow (no files touch WordPress server)
- **Encryption:** AES-256 at rest, TLS 1.3 in transit
- **Virus Scan:** ClamAV via Lambda or ClamAV Docker container
- **Access Control:** Time-limited signed URLs (15-minute expiry)
- **Retention:** Lifecycle policies — raw files 30 days, remediated files 90 days, then Glacier

### 3.5 Document Processing Pipeline (GitHub Submodules)
All processing engines are **GitHub submodules** in `/engines/` directory, synced via PAT:

```
/engines/
  ├── accesspdf/          # Submodule: github.com/laurenaulet/accesspdf
  ├── pdf-acc-toolset/    # Submodule: github.com/aMytho/Pdf-Acc-Toolset
  ├── asu-pdf-access/     # Submodule: github.com/ASUCICREPO/PDF_Accessibility
  ├── docx-accessibility/ # Submodule: (to be sourced)
  └── pptx-remediation/   # Submodule: (to be sourced)
```

**Submodule Management via GitHub PAT:**
```bash
# .github/workflows/sync-submodules.yml
# Runs daily via cron, uses GH_PAT env var
- name: Sync Submodules
  run: |
    git submodule update --remote --merge
    git add .
    git commit -m "chore: sync remediation engines"
    git push
```

---

## 4. GitHub Repositories as Submodules (The Processing Engines)

### 4.1 Primary: accesspdf (Python — PDF Remediation)
**Repo:** `github.com/laurenaulet/accesspdf`  
**License:** Apache 2.0  
**Stars:** ~2.5k  
**Tech:** Python, CLI + Web UI, Ollama/Gemini/Claude/OpenAI support

**Capabilities:**
- Automatic structural fixes (tags, reading order, headings, tables, links, bookmarks)
- AI-powered alt-text generation (local via Ollama or cloud APIs)
- Batch processing entire directories
- Sidecar YAML workflow for human review
- WCAG 2.1 AA + PDF/UA target compliance

**Integration Pattern:**
```python
# WordPress custom endpoint calls this via subprocess or HTTP
import subprocess
result = subprocess.run([
    'python', '-m', 'accesspdf',
    'fix', input_pdf, '-o', output_pdf,
    '--provider', 'gemini',
    '--api-key', os.environ['GEMINI_API_KEY']
], capture_output=True)
```

**Why It's Perfect:**
- Open source, Apache 2.0 (commercial use OK)
- CLI-first = easy to wrap in API
- AI alt-text with human review loop
- Never modifies original file (audit trail)

### 4.2 Secondary: ASU PDF Accessibility (AWS Serverless)
**Repo:** `github.com/ASUCICREPO/PDF_Accessibility`  
**License:** Open Source (ASU)  
**Tech:** AWS CDK, Lambda, Step Functions, ECS Fargate, Bedrock

**Capabilities:**
- PDF-to-PDF remediation (maintains format)
- PDF-to-HTML remediation (accessible web version)
- One-click AWS deployment
- CloudWatch monitoring + dashboards

**Integration Pattern:**
- Deploy as secondary pipeline for enterprise clients
- Trigger via S3 event when file uploaded
- Return results to WordPress via webhook

### 4.3 Tertiary: Pdf-Acc-Toolset (.NET Blazor WASM)
**Repo:** `github.com/aMytho/Pdf-Acc-Toolset`  
**License:** AGPL v3 (community iText)  
**Tech:** .NET 8, Blazor WASM, iText, TailwindCSS

**Capabilities:**
- Browser-based PDF tag manipulation (no server needed)
- List/table generation, tag shifting, color contrast fixing
- Attribute batch modification
- Empty tag removal

**Integration Pattern:**
- Embed as "Manual Review Tool" in client dashboard
- Client can fine-tune automated results before final download
- Runs entirely client-side (privacy win)

### 4.4 Word/PowerPoint Processing (To Be Sourced)
**Gap:** Need open-source DOCX and PPTX remediation engines  
**Research Targets:**
- `python-docx` + custom accessibility tag injection
- `python-pptx` + slide reading order fixes
- Pandoc + custom filters for structured HTML export
- LibreOffice headless mode + UNO API for batch conversion

**Recommendation:** Start with PDF (highest demand), add Word/PowerPoint in Phase 2 using Pandoc + custom post-processing.

---

## 5. The Quote Calculator System

### 5.1 Dynamic Pricing Engine
**Endpoint:** `POST /wp-json/triangle/v1/quote`

**Pricing Variables:**
| Factor | Weight | Calculation |
|--------|--------|-------------|
| Page Count | Base | $2.50/page (simple) / $5.00/page (complex) |
| Document Type | Multiplier | PDF ×1.0, Word ×1.2, PowerPoint ×1.5 |
| Complexity Score | AI-determined | Images/charts/tables detected via preflight |
| Turnaround Time | Urgency | Standard (5-day) ×1.0, Express (48h) ×1.5, Rush (24h) ×2.0 |
| Volume Discount | Tier | 100+ pages: 10% off, 500+: 20% off, 1000+: 30% off |
| Compliance Level | Standard | WCAG 2.1 AA (default), Section 508 (+10%), PDF/UA (+15%) |

**Preflight AI Analysis:**
Before quote, run `accesspdf check` on uploaded file:
- Count pages, images, tables, forms
- Detect scanned vs. text-based
- Assess current accessibility score
- Return complexity score 1-10

**Quote Response:**
```json
{
  "quote_id": "QT-2026-001234",
  "document_name": "Annual_Report_2025.pdf",
  "pages": 47,
  "complexity_score": 6.3,
  "complexity_label": "Moderate",
  "breakdown": {
    "base_cost": 117.50,
    "type_multiplier": 1.0,
    "urgency_multiplier": 1.0,
    "volume_discount": 0.0,
    "compliance_addon": 0.0
  },
  "total": 117.50,
  "turnaround_options": {
    "standard": { "days": 5, "price": 117.50 },
    "express": { "days": 2, "price": 176.25 },
    "rush": { "days": 1, "price": 235.00 }
  },
  "expires_at": "2026-08-09T18:36:00Z",
  "preflight_report": { /* detailed findings */ }
}
```

### 5.2 Implementation (No Paid Plugins)
Build as **custom WordPress REST API endpoint** + React component in Next.js:
- WordPress stores quote templates as JSON in `wp_options`
- Next.js fetches via API and renders interactive calculator
- All math done client-side (instant) + server-side validation (security)

---

## 6. Secure File Upload & Download Architecture

### 6.1 Upload Flow (Pre-Signed URL Pattern)
```
Client → Next.js API → WordPress REST → S3 Pre-Signed URL → Client uploads directly to S3
```

**Why This Pattern:**
- Files never touch WordPress server (no memory/timeout issues)
- Scales to gigabyte files
- Direct-to-S3 = faster upload, lower server load
- Virus scan triggered by S3 event (Lambda)

### 6.2 Download Flow (Signed URL + Audit)
```
Client requests download → WordPress validates permissions → Generates signed URL (15min) → Logs audit entry → Returns URL
```

**Audit Trail (Custom Post Type: `download_log`):**
- User ID, IP address, timestamp, file ID, order ID
- GDPR/SOC 2 compliant retention

### 6.3 Storage Architecture
```
S3 Bucket Structure:
  triangle-uploads/
    ├── raw/          # Original client uploads (encrypted, 30-day retention)
    ├── processing/   # Working files during remediation
    ├── remediated/   # Final output files (encrypted, 90-day retention)
    ├── reports/      # Accessibility reports (JSON + PDF)
    └── archives/     # Long-term Glacier storage (1+ year)
```

---

## 7. Aesthetic Design Direction

### 7.1 Visual Identity: "Clinical Precision + Human Warmth"
**Goal:** Look like a premium medical/legal service, not a cheap SaaS factory.

**Color Palette:**
- Primary: `#0A2540` (Deep Navy — trust, professionalism)
- Secondary: `#00D4AA` (Teal — accessibility, growth, Triangle NC connection)
- Accent: `#FF6B35` (Warm Orange — action, urgency for quotes)
- Background: `#F6F9FC` (Cool Gray — clean, clinical)
- Text: `#1A1A2E` (Near Black — readability)

**Typography:**
- Headings: `Inter` or `Geist` (Sans-serif, geometric, modern)
- Body: `Source Serif 4` or `Merriweather` (Serif for trust, readability)
- Monospace: `JetBrains Mono` (for code samples, API docs)

**Key Design Patterns:**
1. **Glassmorphism Cards** — Subtle frosted glass for quote calculator, file cards
2. **Micro-Animations** — Progress bars with smooth easing, file upload particles
3. **Accessibility-First** — WCAG 2.1 AA on the marketing site itself (dogfooding)
4. **Dark Mode** — Professional dark theme for client dashboard (reduces eye strain)
5. **Data Visualization** — Real-time pipeline status, compliance score gauges

### 7.2 Homepage Sections (Above Fold)
1. **Hero:** "Make Every Document Accessible. Instantly." + live quote calculator
2. **Trust Bar:** WCAG 2.1 AA badge, Section 508 badge, ADA compliance badge, client count
3. **Social Proof:** Rotating testimonials from NC Triangle universities/healthcare
4. **Live Stats:** "2,847 documents remediated this month" (real counter)
5. **Risk Reversal:** "100% compliance guarantee or your money back"

### 7.3 Client Dashboard Design
- **Kanban-style Order Board:** Upload → Preflight → Remediation → Review → Complete
- **File Cards:** Thumbnail preview, compliance score badge, download button, share link
- **Team Management:** Invite colleagues, role-based access (viewer, editor, admin)
- **Analytics:** Monthly spend, document types, compliance trends
- **API Keys:** Self-service API key generation for enterprise integrations

---

## 8. Marketing Strategy: "Mixture of Experts + Social Domination"

### 8.1 Positioning: The "Triangle Advantage"
**Narrative:** "Born in the Research Triangle — trusted by UNC, Duke, NC State, and 200+ healthcare organizations. Local expertise, global standards."

**Why This Works:**
- NC Triangle = instant credibility (top universities, pharma, tech)
- Local SEO advantage for "accessibility remediation North Carolina"
- B2B buyers trust regional expertise for compliance services

### 8.2 Content Mixture of Experts (MoE)
**5 Expert Personas, 5 Content Streams:**

| Expert | Channel | Content Type | Frequency |
|--------|---------|-------------|-----------|
| **The Compliance Lawyer** | LinkedIn | ADA lawsuit breakdowns, DOJ guidance analysis | 3x/week |
| **The Technical Auditor** | Blog/YouTube | WCAG 2.2 deep dives, screen reader demos | 2x/week |
| **The Design Advocate** | Instagram/TikTok | Before/after accessibility transformations | 5x/week |
| **The Enterprise CIO** | LinkedIn Newsletter | B2B procurement guides, RFP templates | 1x/week |
| **The Data Scientist** | Blog/Whitepapers | Accessibility ROI studies, compliance benchmarks | 1x/month |

### 8.3 Social Media Strategy
**LinkedIn (Primary B2B Channel):**
- **Monday:** Case study snippet ("How UNC Health saved $50K in legal fees")
- **Wednesday:** Educational carousel ("5 PDF mistakes that trigger ADA lawsuits")
- **Friday:** Industry news commentary ("New DOJ guidance on digital accessibility")
- **Live Events:** Monthly "Accessibility Hour" LinkedIn Live with Q&A

**Twitter/X (Thought Leadership):**
- Real-time ADA lawsuit tracking ("New filing: Major retailer sued for $5M")
- WCAG tip threads (viral format)
- Engage with accessibility advocates, disability rights organizations

**YouTube (SEO + Education):**
- "How to check your PDF for accessibility" (tutorial, ranks #1)
- "Screen reader demo: Before vs. After remediation" (emotional, shareable)
- "ADA lawsuit explained in 90 seconds" (newsjacking)

**TikTok/Instagram Reels (Awareness):**
- "POV: You're a screen reader trying to read this PDF" (viral potential)
- "Accessibility tip in 15 seconds" series
- Behind-the-scenes: "How we remediate 1000 pages/day"

### 8.4 Competitive Conquest Strategy
**Target 247accessibledocuments.com Keywords:**
- Write comparison page: "Triangle Accessibility vs. 247 Accessible Documents"
- Target their brand name in Google Ads (if budget allows)
- Create "Why we built this" narrative contrasting their opaque pricing vs. your transparency

**Review Harvesting Strategy:**
- G2, Capterra, TrustRadius listings (free profiles)
- Incentivize reviews: "Leave a review, get 10% off next order"
- Video testimonials: "Why [Client] switched from 247 to Triangle"

### 8.5 Lead Generation Funnel
1. **Top:** Free PDF accessibility checker tool (lead magnet)
2. **Middle:** "Get instant quote" (email capture + quote ID)
3. **Bottom:** "Schedule remediation" (Stripe checkout or invoice)
4. **Retention:** Monthly accessibility audit subscription (recurring revenue)

---

## 9. Implementation Roadmap

### Phase 1: MVP (Weeks 1-4)
- [ ] Set up headless WordPress on subdomain (admin.triangleaccessibility.com)
- [ ] Deploy Next.js frontend (Vercel, free tier)
- [ ] Configure PostgreSQL (Supabase free tier)
- [ ] Build custom REST API plugin (quote + upload + status)
- [ ] Integrate `accesspdf` submodule (PDF processing)
- [ ] Build quote calculator (React component)
- [ ] Stripe checkout integration (test mode)
- [ ] Basic client dashboard (order list, download)

### Phase 2: Polish (Weeks 5-8)
- [ ] Add Word/PowerPoint support (Pandoc pipeline)
- [ ] Build preflight AI analysis (complexity scoring)
- [ ] Add team/multi-tenancy features
- [ ] Implement full audit logging
- [ ] Dark mode + accessibility polish
- [ ] G2/Capterra profile setup
- [ ] LinkedIn content calendar launch
- [ ] First case study (pro bono for local nonprofit)

### Phase 3: Scale (Weeks 9-12)
- [ ] Enterprise API (self-service keys)
- [ ] SAML SSO (BoxyHQ integration)
- [ ] Webhook automation (Zapier/Make.com)
- [ ] Affiliate/referral program
- [ ] White-label option for agencies
- [ ] SOC 2 Type II audit preparation
- [ ] Hire first remediation specialist (human QA)

---

## 10. Security & Compliance Checklist

### 10.1 Technical Security
- [ ] All API endpoints require JWT authentication
- [ ] Rate limiting: 100 requests/minute per IP, 1000 per authenticated user
- [ ] File upload: Max 50MB, whitelist MIME types, virus scan
- [ ] SQL injection prevention (prepared statements only)
- [ ] XSS protection (Content Security Policy headers)
- [ ] CORS: Whitelist only triangleaccessibility.com
- [ ] Encryption: AES-256 at rest, TLS 1.3 in transit
- [ ] Backup: Daily automated backups (WordPress + Database + S3)

### 10.2 Compliance
- [ ] WCAG 2.1 AA on marketing site (dogfooding)
- [ ] GDPR: Cookie consent, data deletion request form, DPO contact
- [ ] CCPA: "Do Not Sell My Info" (if applicable)
- [ ] SOC 2 Type I (by Month 6)
- [ ] HIPAA BAA (if serving healthcare — critical for Triangle market)
- [ ] Section 508 VPAT template ready

### 10.3 GitHub PAT Security
- [ ] Use fine-grained PAT (not classic) with minimal scopes
- [ ] Rotate PAT every 90 days
- [ ] Store PAT in GitHub Secrets (never in code)
- [ ] Enable branch protection on all submodule repos
- [ ] Dependabot alerts enabled for all submodules

---

## 11. Cost Breakdown (Monthly, Startup Phase)

| Service | Provider | Cost | Notes |
|---------|----------|------|-------|
| Domain | Porkbun (already owned) | $0 | — |
| WordPress Hosting | Cloudways / Kinsta | $30-50 | Managed, secure |
| Next.js Hosting | Vercel Pro | $20 | Analytics, previews |
| Database | Supabase / Neon | $0 | Free tier sufficient |
| File Storage | Cloudflare R2 | $0-5 | 10GB free, then $0.015/GB |
| Auth | Clerk / Auth.js | $0-25 | Clerk free to 10k MAU |
| Email | Resend | $0 | 3,000 emails/month free |
| Monitoring | Sentry | $0 | 5k errors/month free |
| AI (Alt-text) | Gemini API | $0-20 | Free tier: 1,500 requests/day |
| **Total** | | **~$50-120/month** | |

---

## 12. GitHub Submodule Management Script

```bash
#!/bin/bash
# scripts/sync-engines.sh
# Run via cron or GitHub Actions

set -e

REPOS=(
  "https://github.com/laurenaulet/accesspdf.git:engines/accesspdf"
  "https://github.com/aMytho/Pdf-Acc-Toolset.git:engines/pdf-acc-toolset"
  "https://github.com/ASUCICREPO/PDF_Accessibility.git:engines/asu-pdf-access"
)

for repo in "${REPOS[@]}"; do
  IFS=':' read -r url path <<< "$repo"
  if [ -d "$path/.git" ]; then
    echo "Updating $path..."
    git -C "$path" pull origin main
  else
    echo "Cloning $url into $path..."
    git submodule add "$url" "$path" || true
  fi
done

git add .
git commit -m "chore: sync remediation engines $(date +%Y-%m-%d)" || true
git push
```

---

## 13. Recommended Next Steps

1. **Immediate:** Clone `ixartz/SaaS-Boilerplate` and `nextjs/saas-starter`, evaluate both
2. **Day 2:** Set up WordPress on staging subdomain, install WPGraphQL + ACF
3. **Day 3:** Build custom REST API plugin skeleton (quote endpoint)
4. **Day 4:** Integrate `accesspdf` submodule, test CLI pipeline
5. **Day 5:** Build quote calculator React component
6. **Week 2:** File upload/download flow with S3 pre-signed URLs
7. **Week 3:** Client dashboard + order management
8. **Week 4:** Stripe integration + go-live

---

## 14. Key Differentiators (Why You'll Win)

1. **Transparency:** Instant quotes vs. hidden pricing
2. **Speed:** AI preflight + automated pipeline vs. manual queues
3. **Control:** Full API + webhooks vs. email-only communication
4. **Local:** Research Triangle credibility vs. anonymous offshore
5. **Open:** Open-source processing engines vs. black-box tools
6. **Security:** SOC 2-aligned + HIPAA-ready vs. basic hosting
7. **Marketing:** Data-driven content engine vs. static brochure site

---

*This blueprint is designed to be LLM-parsable, API-actionable, and immediately implementable. Every component is either open-source or has a generous free tier. No paid WordPress plugins required. All processing engines are GitHub submodules managed via PAT.*

**Questions? Iterate on this doc. Let's build.**
