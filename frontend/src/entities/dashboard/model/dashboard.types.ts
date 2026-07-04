export type DomainCoverage = {
  domain: string;
  n_processes: number;
  n_publications: number;
};

export type KnowledgeGap = {
  material: string;
  process: string;
  condition: string;
};

export type GeographyOnlyTopic = {
  entity: string;
  type: string;
  only_geography: string;
};

export type LowSourceEntity = {
  entity: string;
  type: string;
  source_count: number;
};

export type ContradictionPair = {
  node_a: string;
  type_a: string;
  source_a: string | null;
  node_b: string;
  type_b: string;
  source_b: string | null;
};

export type DashboardSummary = {
  coverage_by_domain: DomainCoverage[];
  gaps: KnowledgeGap[];
  geography_only_topics: GeographyOnlyTopic[];
  risk_low_sources: LowSourceEntity[];
  risk_contradictions: ContradictionPair[];
};
