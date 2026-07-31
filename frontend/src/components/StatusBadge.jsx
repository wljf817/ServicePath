export default function StatusBadge({status = "waiting", children}) {
    return (
        <span className={`status-badge status-${status}`}>
            <i aria-hidden="true" />
            {children || status}
        </span>
    );
}
