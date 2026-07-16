import { useCallback, useMemo, useRef } from "react";

import OverlayContext from "./OverlayContext";
import OverlayManager from "./OverlayManager";

export default function OverlayProvider({ children }) {
    const managerRef = useRef(null);

    const open = useCallback(
        (descriptor) => managerRef.current?.open(descriptor),
        []
    );

    const close = useCallback((id) => managerRef.current?.close(id), []);

    const closeAll = useCallback(() => managerRef.current?.closeAll(), []);

    const replace = useCallback(
        (id, descriptor) => managerRef.current?.replace(id, descriptor),
        []
    );

    const update = useCallback(
        (id, props) => managerRef.current?.update(id, props),
        []
    );

    const isOpen = useCallback(
        (id) => managerRef.current?.isOpen(id) ?? false,
        []
    );

    const value = useMemo(
        () => ({ open, close, closeAll, replace, update, isOpen }),
        [open, close, closeAll, replace, update, isOpen]
    );

    return (
        <OverlayContext.Provider value={value}>
            {children}
            <OverlayManager ref={managerRef} />
        </OverlayContext.Provider>
    );
}
