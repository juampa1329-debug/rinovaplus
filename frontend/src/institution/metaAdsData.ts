export type Metrics = Record<
  | "spend"
  | "impressions"
  | "clicks"
  | "reach"
  | "leads"
  | "ctr"
  | "cpc"
  | "cpl"
  | "cpm"
  | "conversations",
  number | null
>;
export type AdObject = {
  id: string;
  name: string;
  status?: string;
  effective_status?: string;
  campaign_id?: string;
  adset_id?: string;
  objective?: string;
  creative?: {
    title: string;
    body: string;
    image_url: string;
    destination_url: string;
  };
};
export type Snapshot = {
  synced_at: string;
  no_delivery: boolean;
  account: { id: string; name: string; currency: string; timezone: string };
  period: { start: string; end: string };
  totals: Metrics;
  daily: (Metrics & { date: string })[];
  campaigns: AdObject[];
  adsets: AdObject[];
  ads: AdObject[];
  ad_insights: (Metrics & {
    ad_id: string;
    campaign_id: string;
    adset_id: string;
  })[];
};

// Reach is unique people across a period; summing daily/ad reach invents people.
export function objectMetrics(
  snapshot: Snapshot,
  entity: "campaigns" | "adsets" | "ads",
  id: string,
): Metrics | null {
  const field =
    entity === "campaigns"
      ? "campaign_id"
      : entity === "adsets"
        ? "adset_id"
        : "ad_id";
  const found = snapshot.ad_insights.filter((v) => v[field] === id);
  if (!found.length) return null;
  const sum = (key: keyof Metrics) =>
    found.every((v) => v[key] !== null)
      ? found.reduce((n, v) => n + v[key]!, 0)
      : null;
  const spend = sum("spend"),
    clicks = sum("clicks"),
    impressions = sum("impressions"),
    leads = sum("leads");
  return {
    spend,
    clicks,
    impressions,
    leads,
    reach: entity === "ads" && found.length === 1 ? found[0].reach : null,
    conversations: sum("conversations"),
    ctr: clicks !== null && impressions ? (clicks / impressions) * 100 : null,
    cpc: spend !== null && clicks ? spend / clicks : null,
    cpl: spend !== null && leads ? spend / leads : null,
    cpm: spend !== null && impressions ? (spend / impressions) * 1000 : null,
  };
}

export function safeAdUrl(value: string) {
  try {
    const url = new URL(value);
    return url.protocol === "https:" && !url.username && !url.password
      ? url.href
      : undefined;
  } catch {
    return undefined;
  }
}
export function formatMetric(
  value: number | null | undefined,
  currency?: string,
) {
  if (value === null || value === undefined) return "—";
  return new Intl.NumberFormat(
    "es-CO",
    currency
      ? { style: "currency", currency, maximumFractionDigits: 2 }
      : { maximumFractionDigits: 2 },
  ).format(value);
}
