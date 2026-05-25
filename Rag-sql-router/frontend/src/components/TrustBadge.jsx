import { ShieldCheck, ShieldAlert, Shield } from 'lucide-react';

export default function TrustBadge({ score }) {
  if (score === null || score === undefined) return null;

  const percentage = Math.round(score * 100);
  let color, Icon, label;

  if (percentage >= 70) {
    color = 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300';
    Icon = ShieldCheck;
    label = 'High Trust';
  } else if (percentage >= 50) {
    color = 'bg-amber-500/10 border-amber-500/20 text-amber-300';
    Icon = Shield;
    label = 'Medium Trust';
  } else {
    color = 'bg-red-500/10 border-red-500/20 text-red-300';
    Icon = ShieldAlert;
    label = 'Low Trust';
  }

  return (
    <span className={`inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-lg border ${color}`}>
      <Icon className="w-3 h-3" />
      {percentage}% {label}
    </span>
  );
}
