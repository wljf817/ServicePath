export function mergeSettings(browser, server) {
    const presetReady = server.presets.some(({id}) => id === browser.preset_id);
    const customReady = Boolean(browser.openai_api_key && browser.openai_model);
    const defaultProvider = server.presets.length && !presetReady && !customReady
        ? {preset_id: server.presets[0].id, provider_type: "preset"}
        : {};
    return {
        ...browser,
        ...defaultProvider,
        presets: server.presets,
        server_presets: server.server_presets,
    };
}
