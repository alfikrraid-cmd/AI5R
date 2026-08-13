import { LiveStreamProvider } from "./context/LiveStreamContext";
import PlatformShell from "./platform/PlatformShell";

export { PUMP_WORKSPACE_ROUTE, PM_WORKSPACE_ROUTE } from "./platform/ApplicationAdapter";

function App() {
    return (
        <LiveStreamProvider>
            <PlatformShell />
        </LiveStreamProvider>
    );
}

export default App;
