import type { Report } from "./types";

export const japanReport: Report = {
  id: "rep_japan_ff",
  request: {
    target_country: "Japan",
    business_type: "fast fashion",
    home_country: "United States",
    budget: 20000,
    currency: "USD",
  },
  verdict: "PROCEED WITH CAUTION",
  confidence: 68,
  executive_summary:
    "Japan is a mature, high-spend fashion market with strong mobile commerce, but fast-fashion is dominated by domestic incumbents (Uniqlo, GU) and imported peers (Zara, H&M). A $20k budget is enough for a validated 90-day test focused on Instagram and LINE, but insufficient for broad brand-building. Cultural fit, sizing localization, and logistics are the biggest blockers.",
  market_data: {
    population: 124500000,
    gdp_per_capita: 33800,
    internet_penetration: 93,
    mobile_subscriptions: 161000000,
    data_year: "2024",
  },
  platform_recommendations: [
    { platform: "Instagram", interest_score: 88, rank: 1, rationale: "Highest fashion discovery intent among 18-34 urban women." },
    { platform: "LINE", interest_score: 82, rank: 2, rationale: "Dominant messaging + LINE Ads Platform reaches 95M MAU in Japan." },
    { platform: "TikTok", interest_score: 74, rank: 3, rationale: "Fast-growing for Gen Z fashion; lower CPM but weaker checkout intent." },
    { platform: "YouTube", interest_score: 61, rank: 4, rationale: "Strong for haul/review content; high production cost per asset." },
    { platform: "X (Twitter)", interest_score: 48, rank: 5, rationale: "High DAU in Japan but weak commercial conversion for apparel." },
  ],
  budget_allocation: [
    { platform: "Instagram", percentage: 45, amount: 9000 },
    { platform: "LINE", percentage: 25, amount: 5000 },
    { platform: "TikTok", percentage: 20, amount: 4000 },
    { platform: "Creative & Localization", percentage: 10, amount: 2000 },
  ],
  risks: [
    { title: "Sizing mismatch", severity: "high", description: "US size grading runs 1-2 sizes large; without JP-specific sizing, return rates typically exceed 30%." },
    { title: "Incumbent price pressure", severity: "medium", description: "Uniqlo and GU set aggressive price anchors; positioning above ¥3,000/item requires clear differentiation." },
    { title: "Payment method coverage", severity: "medium", description: "Konbini and carrier billing account for ~28% of e-commerce; card-only checkouts leak conversions." },
    { title: "Ad account approval delay", severity: "low", description: "LINE Ads onboarding for foreign advertisers can take 2-3 weeks." },
  ],
  next_steps: [
    "Localize product pages and size charts into Japanese (native review, not MT).",
    "Set up LINE Official Account and apply for LINE Ads Platform access.",
    "Run a 4-week Instagram Reels test with 3 creator partnerships (¥300k-500k each).",
    "Add Konbini payment via Stripe or GMO Payment Gateway before scaling.",
    "Re-evaluate after 90 days against CPA ¥3,500 and 2.5%+ ROAS thresholds.",
  ],
  citations: [
    { id: 1, source: "World Bank", detail: "Japan population, 2024 estimate", url: "https://data.worldbank.org/country/japan" },
    { id: 2, source: "World Bank", detail: "GDP per capita (current US$), Japan 2024", url: "https://data.worldbank.org/indicator/NY.GDP.PCAP.CD" },
    { id: 3, source: "Google Trends", detail: "12-month search interest: fast fashion terms in JP", url: "https://trends.google.com/" },
    { id: 4, source: "LINE Corp", detail: "LINE Japan monthly active user count 2024", url: "https://linecorp.com/" },
  ],
  cost: {
    total_tokens_in: 18420,
    total_tokens_out: 6210,
    usd: 0.184,
    per_agent: [
      { agent: "DataAgent", tokens_in: 6100, tokens_out: 1800 },
      { agent: "PlatformAgent", tokens_in: 4900, tokens_out: 1600 },
      { agent: "StrategyAgent", tokens_in: 4600, tokens_out: 1800 },
      { agent: "CriticAgent", tokens_in: 2820, tokens_out: 1010 },
    ],
  },
  verification: {
    checked: true,
    flags: ["Interest scores are directional (Google Trends) — treat as relative signal, not absolute demand."],
    note: "Critic reviewed 4 claims; 1 flagged for context.",
  },
  agent_briefs: {
    data: "Pulled macro indicators from World Bank (2024), cross-checked with METI e-commerce stats.",
    platform: "Ranked 5 platforms by fashion-intent Google Trends + platform-reported MAU in JP.",
    strategy: "Allocated budget to platforms with the highest discovery+conversion overlap for apparel.",
  },
};

export const brazilReport: Report = {
  id: "rep_brazil_app",
  request: {
    target_country: "Brazil",
    business_type: "consumer mobile app",
    home_country: "United States",
    budget: 15000,
    currency: "USD",
  },
  verdict: "GO",
  confidence: 82,
  executive_summary:
    "Brazil has one of the most mobile-first, social-media-native populations in the world with low CPMs, mature Pix payments, and strong Instagram + WhatsApp penetration. A $15k budget is realistic for a paid UA test targeting a validated CAC under $2.50.",
  market_data: {
    population: 216400000,
    gdp_per_capita: 9670,
    internet_penetration: 84,
    mobile_subscriptions: 245000000,
    data_year: "2024",
  },
  platform_recommendations: [
    { platform: "Instagram", interest_score: 91, rank: 1, rationale: "Highest consumer app discovery + lowest CPM in LATAM." },
    { platform: "TikTok", interest_score: 87, rank: 2, rationale: "Explosive growth 18-34; strong install intent for lifestyle apps." },
    { platform: "WhatsApp", interest_score: 79, rank: 3, rationale: "Universal reach; use Click-to-WhatsApp ads for onboarding." },
    { platform: "YouTube", interest_score: 66, rank: 4, rationale: "Strong for demo-heavy creative; higher CPI than Meta." },
  ],
  budget_allocation: [
    { platform: "Instagram", percentage: 50, amount: 7500 },
    { platform: "TikTok", percentage: 30, amount: 4500 },
    { platform: "WhatsApp", percentage: 15, amount: 2250 },
    { platform: "Creative", percentage: 5, amount: 750 },
  ],
  risks: [
    { title: "FX volatility", severity: "medium", description: "BRL swings 8-12% quarterly; price local IAP tiers accordingly." },
    { title: "LGPD compliance", severity: "medium", description: "Brazil's data protection law requires explicit consent and DPO for scaled operations." },
    { title: "Android skew", severity: "low", description: "~85% Android — ensure Play Store creative is prioritized over App Store." },
  ],
  next_steps: [
    "Localize app + store listing into Brazilian Portuguese (native).",
    "Enable Pix payment for any in-app purchases.",
    "Launch Meta Advantage+ App Campaign with $50/day per creative variant.",
    "Add Click-to-WhatsApp funnel for support and re-engagement.",
  ],
  citations: [
    { id: 1, source: "World Bank", detail: "Brazil population 2024", url: "https://data.worldbank.org/country/brazil" },
    { id: 2, source: "World Bank", detail: "GDP per capita, Brazil 2024", url: "https://data.worldbank.org/indicator/NY.GDP.PCAP.CD" },
    { id: 3, source: "Google Trends", detail: "Mobile app search interest Brazil, 12mo", url: "https://trends.google.com/" },
  ],
  cost: {
    total_tokens_in: 16800,
    total_tokens_out: 5900,
    usd: 0.168,
    per_agent: [
      { agent: "DataAgent", tokens_in: 5500, tokens_out: 1700 },
      { agent: "PlatformAgent", tokens_in: 4400, tokens_out: 1500 },
      { agent: "StrategyAgent", tokens_in: 4300, tokens_out: 1700 },
      { agent: "CriticAgent", tokens_in: 2600, tokens_out: 1000 },
    ],
  },
  verification: { checked: true, flags: [], note: "All 5 claims verified against sources." },
  agent_briefs: {
    data: "World Bank + Anatel mobile subscription figures cross-checked.",
    platform: "Interest scores derived from Google Trends normalized against LATAM baseline.",
    strategy: "Weighted toward Meta family given lowest CPM/CPI in region.",
  },
};

export const germanyReport: Report = {
  id: "rep_germany_saas",
  request: {
    target_country: "Germany",
    business_type: "B2B SaaS",
    home_country: "United States",
    budget: 30000,
    currency: "USD",
  },
  verdict: "GO",
  confidence: 76,
  executive_summary:
    "Germany is Europe's largest B2B software market with strong SME digitization budgets. Expect longer sales cycles (6-9 months) and GDPR/data-residency scrutiny, but LinkedIn + G2 + targeted content perform well. $30k supports a focused ABM test.",
  market_data: {
    population: 84500000,
    gdp_per_capita: 52700,
    internet_penetration: 96,
    mobile_subscriptions: 107000000,
    data_year: "2024",
  },
  platform_recommendations: [
    { platform: "LinkedIn", interest_score: 92, rank: 1, rationale: "Primary B2B channel; Germany has ~20M LinkedIn users with strong DACH tooling." },
    { platform: "Google Search", interest_score: 84, rank: 2, rationale: "High commercial intent for category keywords in German." },
    { platform: "G2 / Capterra", interest_score: 71, rank: 3, rationale: "Buyer research heavily influenced by review sites in DACH." },
    { platform: "XING", interest_score: 55, rank: 4, rationale: "Still relevant for older enterprise buyers but declining vs LinkedIn." },
  ],
  budget_allocation: [
    { platform: "LinkedIn", percentage: 55, amount: 16500 },
    { platform: "Google Search", percentage: 25, amount: 7500 },
    { platform: "G2 / Capterra", percentage: 15, amount: 4500 },
    { platform: "Content localization", percentage: 5, amount: 1500 },
  ],
  risks: [
    { title: "GDPR + data residency", severity: "high", description: "Enterprise buyers require EU data hosting and DPA; US-only hosting is a common deal-blocker." },
    { title: "Long sales cycles", severity: "medium", description: "Plan for 6-9 month cycles with multiple stakeholders." },
    { title: "German-language content", severity: "medium", description: "English-only site limits mid-market conversions ~40%." },
  ],
  next_steps: [
    "Publish a German-language landing page and 3 pillar articles.",
    "Set up EU data hosting (Frankfurt) and publish a public DPA.",
    "Run LinkedIn ABM against 500 mid-market DACH accounts.",
    "Claim + optimize G2 and Capterra listings with 10+ reviews.",
  ],
  citations: [
    { id: 1, source: "World Bank", detail: "Germany population, 2024", url: "https://data.worldbank.org/country/germany" },
    { id: 2, source: "World Bank", detail: "GDP per capita, Germany 2024", url: "https://data.worldbank.org/indicator/NY.GDP.PCAP.CD" },
    { id: 3, source: "Google Trends", detail: "B2B SaaS category interest DE 12mo", url: "https://trends.google.com/" },
  ],
  cost: {
    total_tokens_in: 19200,
    total_tokens_out: 7100,
    usd: 0.201,
    per_agent: [
      { agent: "DataAgent", tokens_in: 6300, tokens_out: 2000 },
      { agent: "PlatformAgent", tokens_in: 5100, tokens_out: 1800 },
      { agent: "StrategyAgent", tokens_in: 4800, tokens_out: 2100 },
      { agent: "CriticAgent", tokens_in: 3000, tokens_out: 1200 },
    ],
  },
  verification: { checked: true, flags: [], note: "Critic verified against 3 sources." },
  agent_briefs: {
    data: "Destatis + World Bank cross-check for 2024 macro figures.",
    platform: "LinkedIn share of B2B ad spend in DACH is ~55% per eMarketer 2024.",
    strategy: "ABM-first given long cycles and high ACV expectations.",
  },
};
