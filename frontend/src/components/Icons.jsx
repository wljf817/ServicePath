import {
    Activity,
    ArrowRight,
    ChevronDown,
    Clock3,
    Copy,
    Globe2,
    History,
    Settings,
    SquareTerminal,
} from "lucide-react";


function decorative(Icon) {
    return function DecorativeIcon({className = "", size = 20}) {
        return <Icon aria-hidden="true" className={className} size={size} />;
    };
}


export const ActivityIcon = decorative(Activity);
export const ArrowIcon = decorative(ArrowRight);
export const ChevronIcon = decorative(ChevronDown);
export const ClockIcon = decorative(Clock3);
export const CopyIcon = decorative(Copy);
export const GlobeIcon = decorative(Globe2);
export const HistoryIcon = decorative(History);
export const SettingsIcon = decorative(Settings);
export const TerminalIcon = decorative(SquareTerminal);


export function LogoMark({size = 22}) {
    return (
        <svg aria-hidden="true" fill="none" height={size} viewBox="0 0 24 24" width={size}>
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
