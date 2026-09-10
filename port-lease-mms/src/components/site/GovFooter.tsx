import { Link } from "@tanstack/react-router";

export function GovFooter() {
  return (
    <footer className="mt-16 border-t border-border bg-navy text-navy-foreground">
      <div className="mx-auto grid max-w-7xl gap-8 px-4 py-10 md:grid-cols-4">
        <div>
          <div className="font-display text-base font-semibold">
            Port Estate & Land Management System (AI-PMS)
          </div>
          <p className="mt-2 text-sm text-white/70">
            Enterprise Land & Lease Administration Platform for Major Port Authorities.
          </p>
        </div>
        <div>
          <div className="mb-3 text-sm font-semibold">Quick Links</div>
          <ul className="space-y-2 text-sm text-white/80">
            <li><Link to="/land-monitoring" className="hover:text-gold">Land Monitoring</Link></li>
            <li><Link to="/ai-chat" className="hover:text-gold">AI Assistant</Link></li>
            <li><Link to="/about" className="hover:text-gold">About</Link></li>
          </ul>
        </div>
        <div>
          <div className="mb-3 text-sm font-semibold">Legal</div>
          <ul className="space-y-2 text-sm text-white/80">
            <li><a href="#" className="hover:text-gold">Statutory Disclaimer</a></li>
            <li><a href="#" className="hover:text-gold">Privacy Policy</a></li>
            <li><a href="#" className="hover:text-gold">Terms of Use</a></li>
            <li><a href="#" className="hover:text-gold">Accessibility</a></li>
          </ul>
        </div>
        <div>
          <div className="mb-3 text-sm font-semibold">Associated</div>
          <ul className="space-y-2 text-sm text-white/80">
            <li>Major Port Authority</li>
            <li>Estate & Land Directorate</li>
            <li>Digital Operations</li>
            <li>Land Allotment Cell</li>
          </ul>
        </div>
      </div>
      <div className="border-t border-white/10">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-2 px-4 py-4 text-xs text-white/60 md:flex-row">
          <div>© {new Date().getFullYear()} Major Port Authority. All rights reserved.</div>
          <div>Last updated: {new Date().toLocaleDateString("en-IN")}</div>
        </div>
      </div>
    </footer>
  );
}
