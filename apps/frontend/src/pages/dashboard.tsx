import { useParams } from "react-router";
import { useMyOrgs } from "@/lib/api/auth";
import { useMemo } from "react";

const statsCards = [
  { label: "Services", value: "--", description: "Active services" },
  { label: "Projects", value: "--", description: "Total projects" },
  { label: "Workflows", value: "--", description: "Running workflows" },
  { label: "Wiki Pages", value: "--", description: "Documentation pages" },
];

export default function DashboardPage() {
  const { orgSlug } = useParams();
  const { data: orgs } = useMyOrgs();

  const currentOrg = useMemo(
    () => orgs?.find((o) => o.slug === orgSlug),
    [orgs, orgSlug],
  );

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
        <p className="mt-1 text-sm text-slate-500">
          Welcome to {currentOrg?.name ?? "your organization"}
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {statsCards.map((card) => (
          <div
            key={card.label}
            className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
          >
            <p className="text-sm font-medium text-slate-500">{card.label}</p>
            <p className="mt-2 text-3xl font-bold text-slate-900">
              {card.value}
            </p>
            <p className="mt-1 text-xs text-slate-400">{card.description}</p>
          </div>
        ))}
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-900">
          Getting Started
        </h2>
        <p className="mt-2 text-sm text-slate-500">
          Set up your organization by creating projects, registering services,
          and building your knowledge wiki.
        </p>
      </div>
    </div>
  );
}
