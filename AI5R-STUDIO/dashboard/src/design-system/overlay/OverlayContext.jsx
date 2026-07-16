import { createContext, useContext } from "react";

const OverlayContext = createContext(null);

export function useOverlay() {
    return useContext(OverlayContext);
}

export default OverlayContext;
