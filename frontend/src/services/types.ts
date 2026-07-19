export interface ResearchRequest {
  target_country: string;
  business_type: string;
  home_country: string;
  budget: number;
  currency: string;
}

export interface MarketData {
  population: number;
  gdp_per_capita: number;
  internet_penetration: number;
  mobile_subscriptions: number;
  data_year: string;
}

export interface PlatformRec {
  platform: string;
  interest_score: number;
  rank: number;
  rationale: string;
}

export interface BudgetItem {
  platform: string;
  percentage: number;
  amount: number;
}

export interface Risk {
  title: string;
  severity: "low" | "medium" | "high";
  description: string;
}

export interface Citation {
  id: number;
  source: string;
  detail: string;
  url: string | null;
}

export interface CostAgent {
  agent: string;
  tokens_in: number;
  tokens_out: number;
}

export interface Cost {
  total_tokens_in: number;
  total_tokens_out: number;
  usd: number;
  per_agent: CostAgent[];
}

export interface Verification {
  checked: boolean;
  flags: string[];
  note: string;
}

export type Verdict = "GO" | "PROCEED WITH CAUTION" | "NOT YET";

export interface Report {
  id: string;
  request: ResearchRequest;
  verdict: Verdict;
  confidence: number;
  executive_summary: string;
  market_data: MarketData;
  platform_recommendations: PlatformRec[];
  budget_allocation: BudgetItem[];
  risks: Risk[];
  next_steps: string[];
  competitors?: { name: string; note: string }[];
  unit_economics?: { metric: string; value: string; note: string }[];
  regulatory?: { title: string; detail: string }[];
  gtm_timeline?: { phase: string; timeframe: string; actions: string[] }[];
  research_findings?: string[];
  plan?: { goal?: string; gather: string[]; synthesize: string[]; reason?: string };
  reasoning_log?: { node: string; note: string }[];
  iterations?: number;
  citations: Citation[];
  cost: Cost;
  verification: Verification;
  agent_briefs: { data: string; platform: string; strategy: string };
}

export type AgentName = "DataAgent" | "PlatformAgent" | "StrategyAgent" | "CriticAgent";
export type AgentStatus = "queued" | "running" | "done" | "error";

export interface ProgressEvent {
  agent: string;
  status: AgentStatus;
  message: string;
  timestamp: string;
}

export interface ComparisonMarket {
  country: string;
  business_type: string;
  verdict: Verdict;
  confidence: number;
  population: number | null;
  gdp_per_capita: number | null;
  internet_penetration: number | null;
  top_platform: string | null;
  budget: number | null;
  currency: string;
  market_note?: string;
}

export interface ComparisonReport {
  markets: ComparisonMarket[];
  recommendation: { pick: string; reasons: string[] };
  cost?: Cost;
}

export interface RankingItem {
  rank: number;
  country: string;
  score: number;
  verdict: Verdict;
  rationale: string;
  population: number | null;
  gdp_per_capita: number | null;
  internet_penetration: number | null;
}

export interface RankingReport {
  business_type: string;
  budget: number;
  currency: string;
  items: RankingItem[];
  note: string;
  cost?: Cost;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  kind: "text" | "report" | "comparison" | "ranking";
  text?: string;
  report?: Report;
  comparison?: ComparisonReport;
  ranking?: RankingReport;
  created_at: string;
}

export interface ConversationSummary {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages: Message[];
}

export interface Profile {
  name: string;
  email: string;
  avatar_url: string | null;
  usage: {
    total_tokens_in: number;
    total_tokens_out: number;
    total_usd: number;
    runs_count: number;
    monthly_quota_tokens: number;
  };
}
