import {
    forwardRef,
    useCallback,
    useEffect,
    useImperativeHandle,
    useRef,
    useState,
} from "react";
import { createPortal } from "react-dom";

import OverlayRegistry from "./OverlayRegistry";

let overlayIdCounter = 0;

function generateId() {
    overlayIdCounter += 1;
    return `overlay-${overlayIdCounter}`;
}

function resolveComponent(entry) {
    if (entry.component) {
        return entry.component;
    }

    return OverlayRegistry.get(entry.type)?.component ?? null;
}

function OverlayEntry({ entry, index, onClose }) {
    const nodeRef = useRef(null);
    const previousFocusRef = useRef(null);

    const options = entry.options ?? {};
    const dismissible = options.dismissible !== false;
    const backdrop = options.backdrop !== false;
    const closeOnOutside = dismissible && options.closeOnOutside !== false;
    const restoreFocus = options.restoreFocus !== false;

    useEffect(() => {
        previousFocusRef.current = document.activeElement;
        nodeRef.current?.focus?.();

        return () => {
            if (restoreFocus) {
                previousFocusRef.current?.focus?.();
            }
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    useEffect(() => {
        if (backdrop || !closeOnOutside) {
            return undefined;
        }

        function handlePointerDown(event) {
            if (nodeRef.current && !nodeRef.current.contains(event.target)) {
                onClose();
            }
        }

        document.addEventListener("mousedown", handlePointerDown);
        return () =>
            document.removeEventListener("mousedown", handlePointerDown);
    }, [backdrop, closeOnOutside, onClose]);

    const Component = resolveComponent(entry);

    if (!Component) {
        return null;
    }

    return (
        <div
            ref={nodeRef}
            tabIndex={-1}
            style={{
                position: "fixed",
                inset: 0,
                zIndex: 1000 + index * 10,
                pointerEvents: backdrop ? "auto" : "none",
                outline: "none",
            }}
        >
            {backdrop && (
                <div
                    onClick={closeOnOutside ? onClose : undefined}
                    style={{
                        position: "absolute",
                        inset: 0,
                        background: "rgba(2, 6, 23, 0.6)",
                    }}
                />
            )}

            <Component {...entry.props} onClose={onClose} />
        </div>
    );
}

const OverlayManager = forwardRef(function OverlayManager(_props, ref) {
    const [stack, setStack] = useState([]);

    const open = useCallback((descriptor) => {
        const id = descriptor.options?.id ?? generateId();

        const entry = {
            id,
            type: descriptor.type,
            component: descriptor.component,
            props: descriptor.props ?? {},
            options: descriptor.options ?? {},
        };

        setStack((current) => [
            ...current.filter((item) => item.id !== id),
            entry,
        ]);

        return id;
    }, []);

    const close = useCallback((id) => {
        setStack((current) => {
            if (current.length === 0) {
                return current;
            }

            if (id == null) {
                return current.slice(0, -1);
            }

            return current.filter((item) => item.id !== id);
        });
    }, []);

    const closeAll = useCallback(() => {
        setStack([]);
    }, []);

    const replace = useCallback((id, descriptor) => {
        setStack((current) =>
            current.map((item) =>
                item.id === id
                    ? {
                          ...item,
                          type: descriptor.type,
                          component: descriptor.component,
                          props: descriptor.props ?? {},
                      }
                    : item
            )
        );
    }, []);

    const update = useCallback((id, props) => {
        setStack((current) =>
            current.map((item) =>
                item.id === id
                    ? { ...item, props: { ...item.props, ...props } }
                    : item
            )
        );
    }, []);

    const isOpen = useCallback(
        (id) => {
            if (id == null) {
                return stack.length > 0;
            }

            return stack.some((item) => item.id === id);
        },
        [stack]
    );

    useImperativeHandle(
        ref,
        () => ({ open, close, closeAll, replace, update, isOpen }),
        [open, close, closeAll, replace, update, isOpen]
    );

    useEffect(() => {
        if (stack.length === 0) {
            return undefined;
        }

        function handleKeyDown(event) {
            if (event.key !== "Escape") {
                return;
            }

            const top = stack[stack.length - 1];
            const options = top.options ?? {};
            const dismissible = options.dismissible !== false;
            const closeOnEscape = dismissible && options.closeOnEscape !== false;

            if (closeOnEscape) {
                close(top.id);
            }
        }

        document.addEventListener("keydown", handleKeyDown);
        return () => document.removeEventListener("keydown", handleKeyDown);
    }, [stack, close]);

    if (stack.length === 0) {
        return null;
    }

    return createPortal(
        <>
            {stack.map((entry, index) => (
                <OverlayEntry
                    key={entry.id}
                    entry={entry}
                    index={index}
                    onClose={() => close(entry.id)}
                />
            ))}
        </>,
        document.body
    );
});

export default OverlayManager;
