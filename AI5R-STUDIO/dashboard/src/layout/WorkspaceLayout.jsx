import { NavLink, Outlet } from "react-router-dom";

const navItems = [
  ["Home", "/"],
  ["Mission", "/mission"],
  ["Progress", "/progress"],
  ["Result", "/result"],
  ["History", "/history"],
];

export default function WorkspaceLayout() {
  return (
    <div className="workspace">
      <header className="workspaceHeader">
        <div>
          <h2>🌳 AI5R Workspace</h2>
          <small>Describe what you need. AI5R builds it.</small>
        </div>

        <nav>
          {navItems.map(([label, path]) => (
            <NavLink
              key={path}
              to={path}
              className={({ isActive }) => isActive ? "nav activeNav" : "nav"}
            >
              {label}
            </NavLink>
          ))}
        </nav>

        <strong>Chief</strong>
      </header>

      <Outlet />
    </div>
  );
}
