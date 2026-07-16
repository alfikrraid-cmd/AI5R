import InspectorHeader from "./InspectorHeader";

export default function Inspector({ title, actions, children }) {
    return (
        <div
            style={{
                display: "flex",
                flexDirection: "column",
                height: "100%",
                minHeight: 0,
                background: "#0F172A",
                border: "1px solid #1E293B",
                borderRadius: 16,
                overflow: "hidden",
            }}
        >
            <InspectorHeader title={title} actions={actions} />

            <div
                style={{
                    flex: 1,
                    minHeight: 0,
                    overflow: "auto",
                    padding: "12px 0",
                }}
            >
                {children}
            </div>
        </div>
    );
}
