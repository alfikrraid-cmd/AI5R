import { WorkspaceProvider } from "@/design-system/workspace";

export default function Providers({ children }) {
    return (
        <WorkspaceProvider>
            {children}
        </WorkspaceProvider>
    );
}