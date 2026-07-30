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

export function LogoMark({size = 22}) {
    return (
        <svg
            aria-hidden="true"
            fill="none"
            height={size}
            viewBox="0 0 24 24"
            width={size}
        >
            <path
                d="M4 7h5.25A2.75 2.75 0 0 1 12 9.75v4.5A2.75 2.75 0 0 0 14.75 17H20"
                stroke="currentColor"
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="1.8"
            />
            <circle cx="4" cy="7" fill="currentColor" r="1.8" />
            <circle cx="20" cy="17" fill="currentColor" r="1.8" />
        </svg>
    );
}

export function SettingsIcon(props) {
    return (
        <Icon {...props}>
            <path
                d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.38a2 2 0 0 0-.73-2.73l-.15-.09a2 2 0 0 1-1-1.74v-.51a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2Z"
                stroke="currentColor"
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="1.8"
            />
            <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="1.8" />
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
