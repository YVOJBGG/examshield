import type { ReactNode } from "react";

type PageHeaderProps = {
  eyebrow: string;
  title: string;
  description: string;
  backLink?: ReactNode;
  actions?: ReactNode;
};

type StatCardProps = {
  label: string;
  value: ReactNode;
  description: string;
};

type EmptyStateProps = {
  title: string;
  description: string;
  action?: ReactNode;
  className?: string;
};

export function PageHeader({
  eyebrow,
  title,
  description,
  backLink,
  actions,
}: PageHeaderProps) {
  return (
    <div className="page-header dashboard-header">
      <div className="page-heading-block">
        {backLink ? backLink : null}
        <span className="eyebrow">{eyebrow}</span>
        <h2>{title}</h2>
        <p className="page-intro">{description}</p>
      </div>
      {actions ? <div className="actions">{actions}</div> : null}
    </div>
  );
}

export function StatCard({ label, value, description }: StatCardProps) {
  return (
    <article className="stat-card">
      <span className="stat-label">{label}</span>
      <strong>{value}</strong>
      <p>{description}</p>
    </article>
  );
}

export function EmptyState({ title, description, action, className }: EmptyStateProps) {
  return (
    <div className={["empty-state-card", className].filter(Boolean).join(" ")}>
      <h3>{title}</h3>
      <p>{description}</p>
      {action ? action : null}
    </div>
  );
}
