import {useCallback, useEffect, useRef} from "react";

export default function useAbortableTask() {
    const controllerRef = useRef(null);

    const abort = useCallback(() => {
        controllerRef.current?.abort();
        controllerRef.current = null;
    }, []);

    useEffect(() => {
        return () => abort();
    }, [abort]);

    const run = useCallback(async (task) => {
        // A new task replaces the previous one.
        controllerRef.current?.abort();
        const controller = new AbortController();
        controllerRef.current = controller;

        try {
            const value = await task(controller.signal);
            const completed = (
                !controller.signal.aborted
                && controllerRef.current === controller
            );
            return {completed, value: completed ? value : undefined};
        } catch (error) {
            if (
                controller.signal.aborted
                || controllerRef.current !== controller
                || error?.name === "AbortError"
            ) {
                return {completed: false, value: undefined};
            }
            throw error;
        } finally {
            if (controllerRef.current === controller) {
                controllerRef.current = null;
            }
        }
    }, []);

    return {abort, run};
}
