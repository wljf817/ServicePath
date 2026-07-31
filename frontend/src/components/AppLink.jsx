function shouldUseClientNavigation(event) {
    const link = event.currentTarget;

    return (
        event.button === 0
        && !event.defaultPrevented
        && !event.metaKey
        && !event.ctrlKey
        && !event.shiftKey
        && !event.altKey
        && !link.hasAttribute("download")
        && (!link.target || link.target === "_self")
        && new URL(link.href).origin === window.location.origin
    );
}

export default function AppLink({children, href, navigate, onClick, ...props}) {
    function handleClick(event) {
        onClick?.(event);
        if (!shouldUseClientNavigation(event)) {
            return;
        }

        // Preserve native link behavior for modified clicks and external targets.
        event.preventDefault();
        navigate(href);
    }

    return (
        <a href={href} onClick={handleClick} {...props}>
            {children}
        </a>
    );
}
