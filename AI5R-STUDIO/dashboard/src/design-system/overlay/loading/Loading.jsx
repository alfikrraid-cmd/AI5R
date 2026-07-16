import { LoadingState } from "../../feedback";

export default function Loading({ message }) {
    return (
        <div
            style={{
                position: "absolute",
                inset: 0,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
            }}
        >
            <div
                style={{
                    pointerEvents: "auto",
                    background: "#0F172A",
                    border: "1px solid #1E293B",
                    borderRadius: 16,
                    boxShadow: "0 20px 60px rgba(0,0,0,.5)",
                }}
            >
                <LoadingState message={message} />
            </div>
        </div>
    );
}
