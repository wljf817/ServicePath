import {Button} from "@heroui/react";

import {ActivityIcon, HistoryIcon, SettingsIcon} from "./Icons";

export default function Shell({children, path, navigate}) {
    const links = [
        {label: "Diagnostics", path: "/", icon: ActivityIcon},
        {label: "History", path: "/history", icon: HistoryIcon},
        {label: "Settings", path: "/settings", icon: SettingsIcon},
    ];

    return (
        <div className="app-shell">
            <header className="topbar">
                <button className="brand" onClick={() => navigate("/")} type="button">
                    <span className="brand-mark"><ActivityIcon size={21} /></span>
                    <span>
                        <strong>ServicePath</strong>
                        <small>Network diagnostics</small>
                    </span>
                </button>

                <nav className="main-nav" aria-label="Primary navigation">
                    {links.map((link) => {
                        const LinkIcon = link.icon;
                        const active = link.path === "/" ? path === "/" : path.startsWith(link.path);
                        return (
                            <Button
                                className={active ? "nav-button nav-button-active" : "nav-button"}
                                key={link.path}
                                onPress={() => navigate(link.path)}
                                size="sm"
                                variant="ghost"
                            >
                                <LinkIcon size={17} />
                                {link.label}
                            </Button>
                        );
                    })}
                </nav>

                <span className="system-online"><i /> System online</span>
            </header>

            <main className="app-content">{children}</main>

            <footer className="app-footer">
                <span>ServicePath</span>
                <span>Flask · React · HeroUI</span>
            </footer>
        </div>
    );
}
