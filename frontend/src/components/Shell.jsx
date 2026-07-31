import {ActivityIcon, HistoryIcon, LogoMark, SettingsIcon} from "./Icons";
import AppLink from "./AppLink";

export default function Shell({activity, children, path, navigate}) {
    const links = [
        {label: "Diagnostics", path: "/", icon: ActivityIcon},
        {label: "History", path: "/history", icon: HistoryIcon},
        {label: "Settings", path: "/settings", icon: SettingsIcon},
    ];
    const activityLabels = {
        complete: "Report ready",
        error: "Investigation stopped",
        idle: "Interface ready",
        running: "Investigation running",
    };
    const activityStatus = activity?.status || "idle";
    const activityLabel = activity?.label || activityLabels[activityStatus];
    const activityClass = activityStatus === "idle"
        ? "system-online"
        : `system-online system-online-active system-online-${activityStatus}`;

    return (
        <div className="app-shell">
            <div className="ambient-backdrop" aria-hidden="true">
                <span className="ambient-orb ambient-orb-one" />
                <span className="ambient-orb ambient-orb-two" />
                <span className="ambient-grid" />
            </div>
            <header className="topbar">
                <div className="topbar-inner">
                    <AppLink className="brand" href="/" navigate={navigate}>
                        <span className="brand-mark">
                            <LogoMark size={22} />
                        </span>
                        <span className="brand-copy">
                            <strong>ServicePath</strong>
                        </span>
                    </AppLink>

                    <nav className="main-nav" aria-label="Primary navigation">
                        {links.map((link) => {
                            const LinkIcon = link.icon;
                            const active = link.path === "/"
                                ? path === "/" || path.startsWith("/reports/")
                                : path.startsWith(link.path);
                            return (
                                <AppLink
                                    aria-current={active ? "page" : undefined}
                                    className={active ? "nav-button nav-button-active" : "nav-button"}
                                    href={link.path}
                                    key={link.path}
                                    navigate={navigate}
                                >
                                    <LinkIcon size={17} />
                                    <span>{link.label}</span>
                                </AppLink>
                            );
                        })}
                    </nav>

                    <span aria-atomic="true" className="sr-only" role="status">
                        {activityLabel}
                    </span>
                    <span className={activityClass}>
                        <i aria-hidden="true" />
                        {activityStatus === "complete" && activity.reportUrl ? (
                            <AppLink href={activity.reportUrl} navigate={navigate}>Report ready</AppLink>
                        ) : activityLabel}
                    </span>
                </div>
            </header>

            <main
                className={path === "/" ? "app-content app-content-dashboard" : "app-content"}
                id="main-content"
                tabIndex="-1"
            >
                {children}
            </main>

            <footer className="app-footer">
                <div className="footer-identity">
                    <span className="footer-mark"><LogoMark size={18} /></span>
                    <span className="footer-copy">
                        <strong>ServicePath</strong>
                    </span>
                </div>
                <div className="footer-meta" aria-label="Application details">
                    <span>Single-agent diagnostics</span>
                    <i aria-hidden="true" />
                    <span>Flask + React</span>
                </div>
            </footer>
        </div>
    );
}
