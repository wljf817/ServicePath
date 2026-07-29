function Icon({children, size = 20, className = ""}) {
    return (
        <svg
            aria-hidden="true"
            className={className}
            fill="none"
            height={size}
            viewBox="0 0 24 24"
            width={size}
        >
            {children}
        </svg>
    );
}

export function ActivityIcon(props) {
    return (
        <Icon {...props}>
            <path d="M3 12h4l2-7 4 14 2-7h6" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
        </Icon>
    );
}

export function ArrowIcon(props) {
    return (
        <Icon {...props}>
            <path d="M5 12h14m-5-5 5 5-5 5" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
        </Icon>
    );
}

export function ClockIcon(props) {
    return (
        <Icon {...props}>
            <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="2" />
            <path d="M12 7v5l3 2" stroke="currentColor" strokeLinecap="round" strokeWidth="2" />
        </Icon>
    );
}

export function ChevronIcon(props) {
    return (
        <Icon {...props}>
            <path d="m8 10 4 4 4-4" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
        </Icon>
    );
}

export function CopyIcon(props) {
    return (
        <Icon {...props}>
            <rect height="13" rx="2" stroke="currentColor" strokeWidth="1.8" width="13" x="8" y="8" />
            <path d="M16 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h3" stroke="currentColor" strokeLinecap="round" strokeWidth="1.8" />
        </Icon>
    );
}

export function GlobeIcon(props) {
    return (
        <Icon {...props}>
            <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="2" />
            <path d="M3 12h18M12 3c3 3.3 3 14.7 0 18M12 3c-3 3.3-3 14.7 0 18" stroke="currentColor" strokeLinecap="round" strokeWidth="2" />
        </Icon>
    );
}

export function HistoryIcon(props) {
    return (
        <Icon {...props}>
            <path d="M4 7v5h5M5.2 16A8 8 0 1 0 4 12" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
            <path d="M12 8v5l3 2" stroke="currentColor" strokeLinecap="round" strokeWidth="2" />
        </Icon>
    );
}

export function SettingsIcon(props) {
    return (
        <Icon {...props}>
            <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="2" />
            <path d="M19 13.5v-3l-2-.7-.7-1.7.9-1.9-2.1-2.1-1.9.9-1.7-.7-.7-2h-3l-.7 2-1.7.7-1.9-.9-2.1 2.1.9 1.9-.7 1.7-2 .7v3l2 .7.7 1.7-.9 1.9 2.1 2.1 1.9-.9 1.7.7.7 2h3l.7-2 1.7-.7 1.9.9 2.1-2.1-.9-1.9.7-1.7 2-.7Z" stroke="currentColor" strokeLinejoin="round" strokeWidth="1.5" />
        </Icon>
    );
}

export function TerminalIcon(props) {
    return (
        <Icon {...props}>
            <rect height="16" rx="2" stroke="currentColor" strokeWidth="2" width="20" x="2" y="4" />
            <path d="m6 9 3 3-3 3m5 0h5" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
        </Icon>
    );
}
