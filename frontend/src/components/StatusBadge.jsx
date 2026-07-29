export default function StatusBadge({status = "waiting", children}) {
    return (
        <span className={`status-badge status-${status}`}>
            <i />
            {children || status}
        </span>
    );
}
