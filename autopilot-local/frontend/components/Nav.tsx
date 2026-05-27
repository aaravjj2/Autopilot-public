import Link from "next/link";

export function Nav() {
  return (
    <nav data-testid="nav" className="mb-8 flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-4">
      <Link href="/" className="text-xl font-bold tracking-tight text-white" data-testid="nav-home-link">
        Autopilot <span className="text-apex-accent">Local</span>
      </Link>
      <div className="flex gap-4 text-sm">
        <Link href="/" className="text-slate-300 hover:text-white" data-testid="nav-marketplace-link">
          Marketplace
        </Link>
        <Link href="/dashboard" className="text-slate-300 hover:text-white" data-testid="nav-dashboard-link">
          Dashboard
        </Link>
      </div>
    </nav>
  );
}
