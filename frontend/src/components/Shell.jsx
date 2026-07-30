import {ActivityIcon, HistoryIcon, LogoMark, SettingsIcon} from "./Icons";

export default function Shell({children, path, navigate}) {
    const links = [
        {label: "Diagnostics", path: "/", icon: ActivityIcon},
        {label: "History", path: "/history", icon: HistoryIcon},
        {label: "Settings", path: "/settings", icon: SettingsIcon},
    ];

    return (
        <div className="app-shell">
            <div className="ambient-backdrop" aria-hidden="true">
                <span className="ambient-orb ambient-orb-one" />
                <span className="ambient-orb ambient-orb-two" />
                <span className="ambient-grid" />
            </div>
            <header className="topbar">
                <div className="topbar-inner">
                    <button className="brand" onClick={() => navigate("/")} type="button">
                        <span className="brand-mark">
                            <LogoMark size={22} />
                        </span>
                        <span className="brand-copy">
                            <strong>ServicePath</strong>
                        </span>
                    </button>

                    <nav className="main-nav" aria-label="Primary navigation">
                        {links.map((link) => {
                            const LinkIcon = link.icon;
                            const active = link.path === "/"
                                ? path === "/" || path.startsWith("/reports/")
                                : path.startsWith(link.path);
                            return (
                                <button
                                    aria-current={active ? "page" : undefined}
                                    className={active ? "nav-button nav-button-active" : "nav-button"}
                                    key={link.path}
                                    onClick={() => navigate(link.path)}
                                    type="button"
                                >
                                    <LinkIcon size={17} />
                                    <span>{link.label}</span>
                                </button>
                            );
                        })}
                    </nav>

                    <span className="system-online"><i /> Interface ready</span>
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
