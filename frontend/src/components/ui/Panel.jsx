export default function Panel({children, className = "", ...props}) {
    return <section className={className} {...props}>{children}</section>;
}

Panel.Header = function PanelHeader({children, className = "", ...props}) {
    return <header className={className} {...props}>{children}</header>;
};

Panel.Title = function PanelTitle({children, className = "", ...props}) {
    return <h2 className={className} {...props}>{children}</h2>;
};

Panel.Description = function PanelDescription({children, className = "", ...props}) {
    return <p className={`panel-description ${className}`.trim()} {...props}>{children}</p>;
};

Panel.Content = function PanelContent({children, className = "", ...props}) {
    return <div className={className} {...props}>{children}</div>;
};
