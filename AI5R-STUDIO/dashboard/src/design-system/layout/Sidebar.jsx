import { NavLink } from "react-router-dom";

import {
    LayoutDashboard,
    Factory,
    ClipboardList,
    Briefcase,
    Cpu,
    Bot,
    BarChart3,
    Settings,
    ChevronLeft,
} from "lucide-react";

import { sidebarMenu } from "./sidebarMenu";

const icons = {
    Dashboard: LayoutDashboard,
    LTSA: Factory,
    "Auditor OS": ClipboardList,
    "UMKM OS": Briefcase,
    Runtime: Cpu,
    "AI Workforce": Bot,
    Analytics: BarChart3,
    Settings: Settings,
};

export default function Sidebar() {
    return (
        <aside
            style={{
                width: 260,
                background: "#0F172A",
                borderRight: "1px solid #1E293B",
                display: "flex",
                flexDirection: "column",
                color: "#fff",
            }}
        >
            {/* Logo */}

            <div
                style={{
                    padding: "20px",
                    borderBottom: "1px solid #1E293B",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                }}
            >
                <div>
                    <div
                        style={{
                            fontSize: 22,
                            fontWeight: 700,
                        }}
                    >
                        🌳 AI5R
                    </div>

                    <div
                        style={{
                            color: "#94A3B8",
                            fontSize: 12,
                            marginTop: 2,
                        }}
                    >
                        Digital Factory
                    </div>
                </div>

                <ChevronLeft
                    size={18}
                    color="#64748B"
                    style={{
                        cursor: "pointer",
                    }}
                />
            </div>

            {/* Menu */}

            <div
                style={{
                    flex: 1,
                    overflowY: "auto",
                    padding: 20,
                }}
            >
                {sidebarMenu.map((group) => (
                    <div
                        key={group.section}
                        style={{
                            marginBottom: 28,
                        }}
                    >
                        <div
                            style={{
                                color: "#64748B",
                                fontSize: 11,
                                fontWeight: 700,
                                letterSpacing: 1,
                                marginBottom: 12,
                            }}
                        >
                            {group.section}
                        </div>

                        {group.items.map((item) => {
                            const Icon = icons[item.title];

                            return (
                                <NavLink
                                    key={item.path}
                                    to={item.path}
                                    style={({ isActive }) => ({
                                        display: "flex",
                                        alignItems: "center",
                                        gap: 12,
                                        padding: "11px 14px",
                                        marginBottom: 6,
                                        borderRadius: 10,
                                        textDecoration: "none",
                                        fontWeight: isActive ? 600 : 400,
                                        color: isActive
                                            ? "#FFFFFF"
                                            : "#CBD5E1",
                                        background: isActive
                                            ? "#2563EB"
                                            : "transparent",
                                        transition: "0.2s",
                                    })}
                                >
                                    {Icon && <Icon size={18} />}

                                    <span>{item.title}</span>
                                </NavLink>
                            );
                        })}
                    </div>
                ))}
            </div>

            {/* Footer */}

            <div
                style={{
                    padding: 20,
                    borderTop: "1px solid #1E293B",
                }}
            >
                <div
                    style={{
                        fontWeight: 600,
                    }}
                >
                    Sandy Aguswiensyah
                </div>

                <div
                    style={{
                        color: "#64748B",
                        fontSize: 12,
                        marginTop: 4,
                    }}
                >
                    Founder • AI5R
                </div>
            </div>
        </aside>
    );
}