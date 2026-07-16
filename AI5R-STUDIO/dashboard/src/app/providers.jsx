import { WorkspaceProvider } from "@/design-system/workspace";
import StudioProvider from "./StudioProvider";

export default function Providers({ children }) {
    return (
        <WorkspaceProvider>
            <StudioProvider>
                {children}
            </StudioProvider>
        </WorkspaceProvider>
    );
}