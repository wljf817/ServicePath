const basePathElement = document.querySelector(
    'meta[name="servicepath-base-path"]'
);

if (!basePathElement) {
    throw new Error("ServicePath base path configuration is missing.");
}

const basePath = basePathElement.content;

export function appPath(path) {
    if (!path.startsWith("/")) {
        throw new TypeError("Application path must start with a slash.");
    }
    return `${basePath}${path}`;
}

export function currentAppPath() {
    const path = window.location.pathname;
    if (!basePath) {
        return path;
    }
    if (path === basePath) {
        return "/";
    }
    if (!path.startsWith(`${basePath}/`)) {
        throw new Error("Current URL is outside the ServicePath base path.");
    }
    return path.slice(basePath.length);
}
