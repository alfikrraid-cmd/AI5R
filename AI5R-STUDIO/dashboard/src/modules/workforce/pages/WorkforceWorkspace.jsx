import { useEffect, useMemo, useState } from "react";
import {
  createWorkforceMission,
  fetchWorkforceActivities,
  fetchWorkforceBoard,
  fetchWorkforceEmployee,
  fetchWorkforceEmployees,
  fetchWorkforceMetrics,
} from "../../../api/workforceClient";
import { createLiveStreamClient } from "../../../api/liveStreamClient";
import Badge from "../../../design-system/components/Badge";
import Button from "../../../design-system/components/Button";
import EmptyState from "../../../design-system/components/EmptyState";
import SearchBox from "../../../design-system/components/SearchBox";
import Tabs from "../../../design-system/components/Tabs";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import typography from "../../../design-system/theme/typography";
import ActivityFeedView from "../components/ActivityFeedView";
import AssignTaskModal from "../components/AssignTaskModal";
import ChiefApprovalModal from "../components/ChiefApprovalModal";
import DelegateProjectModal from "../components/DelegateProjectModal";
import EmployeeCard from "../components/EmployeeCard";
import EmployeeChatModal from "../components/EmployeeChatModal";
import EmployeeDetailModal from "../components/EmployeeDetailModal";
import MissionDetailModal from "../components/MissionDetailModal";
import TaskDetailModal from "../components/TaskDetailModal";
import WorkforceBoardView from "../components/WorkforceBoardView";
import WorkforceMetricsHeader from "../components/WorkforceMetricsHeader";

const STATUS_FILTERS = [
  { id: "ALL", label: "All Statuses" },
  { id: "AVAILABLE", label: "Available" },
  { id: "WORKING", label: "Working" },
  { id: "WAITING_APPROVAL", label: "Waiting Approval" },
  { id: "OFFLINE", label: "Offline" },
];

export default function WorkforceWorkspace() {
  const [employees, setEmployees] = useState([]);
  const [board, setBoard] = useState({ published: [], claimed: [], completed: [], released: [], summary: {} });
  const [activities, setActivities] = useState([]);
  const [metrics, setMetrics] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [activeTab, setActiveTab] = useState("employees");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [searchQuery, setSearchQuery] = useState("");

  // Inspect Profile Modal state
  const [selectedEmployee, setSelectedEmployee] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Assign Task Modal state
  const [isAssignModalOpen, setIsAssignModalOpen] = useState(false);
  const [assignPreselectedEmployee, setAssignPreselectedEmployee] = useState(null);

  // Employee Chat Modal state & isolated conversations
  const [isChatModalOpen, setIsChatModalOpen] = useState(false);
  const [chatEmployee, setChatEmployee] = useState(null);
  const [conversations, setConversations] = useState({});

  // Task Detail Modal state
  const [isTaskDetailModalOpen, setIsTaskDetailModalOpen] = useState(false);
  const [selectedTask, setSelectedTask] = useState(null);

  // Chief Approval Modal state
  const [isApprovalModalOpen, setIsApprovalModalOpen] = useState(false);
  const [approvingTask, setApprovingTask] = useState(null);

  // Delegate Project Modal & Mission Detail Modal state
  const [isDelegateModalOpen, setIsDelegateModalOpen] = useState(false);
  const [isMissionDetailModalOpen, setIsMissionDetailModalOpen] = useState(false);
  const [activeMission, setActiveMission] = useState(null);
  const [isSubmittingMission, setIsSubmittingMission] = useState(false);

  const [liveStreamConnected, setLiveStreamConnected] = useState(false);

  async function loadData() {
    try {
      setError(null);
      const [empData, boardData, actData, metData] = await Promise.all([
        fetchWorkforceEmployees().catch(() => []),
        fetchWorkforceBoard().catch(() => ({ published: [], claimed: [], completed: [], released: [] })),
        fetchWorkforceActivities({ limit: 50 }).catch(() => []),
        fetchWorkforceMetrics().catch(() => ({})),
      ]);

      setEmployees(empData || []);
      setBoard(boardData || {});
      setActivities(actData || []);
      setMetrics(metData || {});
    } catch (err) {
      setError(err.message || "Failed to load workforce data");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();

    // Connect to realtime live stream (SSE)
    let client;
    try {
      client = createLiveStreamClient({
        endpoint: "/api/studio/events/stream",
        onEvent: (evt) => {
          setLiveStreamConnected(true);
          // On workforce events, refresh state in background
          if (
            evt.event_type?.startsWith("WORKFORCE_") ||
            evt.event_type?.startsWith("EMPLOYEE_") ||
            evt.event_type === "RUNTIME_COMPLETED"
          ) {
            loadData();
          }
        },
        onError: () => {
          setLiveStreamConnected(false);
        },
      });
      setLiveStreamConnected(true);
    } catch {
      setLiveStreamConnected(false);
    }

    return () => {
      client?.close();
    };
  }, []);

  async function handleInspectEmployee(emp) {
    setSelectedEmployee(emp);
    setIsModalOpen(true);
    // Fetch enriched details
    try {
      const detailed = await fetchWorkforceEmployee(emp.employee_id);
      if (detailed) {
        setSelectedEmployee(detailed);
      }
    } catch {
      // Keep basic employee data if detail fetch fails
    }
  }

  function handleOpenAssignTask(emp = null) {
    setAssignPreselectedEmployee(emp);
    setIsAssignModalOpen(true);
  }

  function handleOpenChat(emp) {
    setChatEmployee(emp);
    setIsChatModalOpen(true);
  }

  function handleSelectTask(task) {
    setSelectedTask(task);
    setIsTaskDetailModalOpen(true);
  }

  function handleRequestApproval(task) {
    setApprovingTask(task);
    setIsApprovalModalOpen(true);
  }

  function handleUpdateConversation(empId, conversationData) {
    setConversations((prev) => ({
      ...prev,
      [empId]: conversationData,
    }));
  }

  function handleOpenDelegateProject(_emp = null) {
    setIsDelegateModalOpen(true);
  }

  async function handleDelegateMission({ title, description, isProduction }) {
    setIsSubmittingMission(true);
    try {
      const res = await createWorkforceMission({
        title,
        description,
        isProduction,
      });
      setIsDelegateModalOpen(false);
      if (res?.mission) {
        setActiveMission(res.mission);
        setIsMissionDetailModalOpen(true);
      }
      await loadData();
    } finally {
      setIsSubmittingMission(false);
    }
  }

  const filteredEmployees = useMemo(() => {
    return employees.filter((emp) => {
      if (statusFilter !== "ALL" && emp.status !== statusFilter) {
        return false;
      }
      if (!searchQuery.trim()) {
        return true;
      }
      const q = searchQuery.toLowerCase();
      return (
        emp.employee_name?.toLowerCase().includes(q) ||
        emp.position_id?.toLowerCase().includes(q) ||
        emp.role?.toLowerCase().includes(q) ||
        (emp.skills || []).some((s) => s.toLowerCase().includes(q))
      );
    });
  }, [employees, statusFilter, searchQuery]);

  const tabs = [
    { key: "employees", label: `AI Employees (${employees.length})` },
    { key: "board", label: `Task Center / Board (${board.summary?.total_items ?? 0})` },
    { key: "activities", label: `Activity Feed (${activities.length})` },
  ];

  return (
    <div
      data-testid="workforce-workspace"
      style={{
        display: "flex",
        flexDirection: "column",
        gap: spacing.lg,
        padding: spacing.lg,
      }}
    >
      {/* Top Banner / Identity */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: spacing.md,
        }}
      >
        <div>
          <h2 style={{ margin: 0, fontSize: typography.size.xl, color: colors.text }}>
            AI EMPLOYEES & DIGITAL WORKFORCE
          </h2>
          <div style={{ fontSize: typography.size.xs, color: colors.textMuted, marginTop: spacing.xs / 2 }}>
            Autonomous IT Department · 9 Digital Agents · Real-time Operational Stream
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: spacing.sm, flexWrap: "wrap" }}>
          <button
            type="button"
            data-testid="open-delegate-mission-button"
            onClick={() => handleOpenDelegateProject()}
            style={{
              background: "#4f46e5",
              color: "#ffffff",
              border: "none",
              borderRadius: spacing.xs,
              padding: `${spacing.xs}px ${spacing.md}px`,
              fontWeight: typography.weight.bold,
              cursor: "pointer",
            }}
          >
            ⚡ Delegate Mission (NEXA)
          </button>
          <button
            type="button"
            data-testid="open-assign-task-modal-button"
            onClick={() => handleOpenAssignTask()}
            style={{
              background: colors.info,
              color: colors.text,
              border: "none",
              borderRadius: spacing.xs,
              padding: `${spacing.xs}px ${spacing.md}px`,
              cursor: "pointer",
            }}
          >
            + Assign Task
          </button>
          <Badge variant={liveStreamConnected ? "success" : "info"}>
            {liveStreamConnected ? "● LIVE STREAM ACTIVE" : "○ STREAM READY"}
          </Badge>
          <Button onClick={loadData} disabled={loading}>
            {loading ? "Refreshing..." : "Refresh"}
          </Button>
        </div>
      </div>

      {/* KPI Metrics Header */}
      <WorkforceMetricsHeader metrics={metrics} />

      {/* Error alert if any */}
      {error ? (
        <div
          data-testid="workforce-error-banner"
          style={{
            background: "rgba(239, 68, 68, 0.15)",
            border: `1px solid ${colors.danger}`,
            borderRadius: spacing.xs,
            padding: spacing.md,
            color: colors.danger,
            fontSize: typography.size.sm,
          }}
        >
          {error}
        </div>
      ) : null}

      {/* Main Tab Navigation */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: spacing.md }}>
        <Tabs items={tabs} activeKey={activeTab} onChange={setActiveTab} />

        {activeTab === "employees" ? (
          <div style={{ display: "flex", gap: spacing.sm, alignItems: "center", flexWrap: "wrap" }}>
            <SearchBox
              placeholder="Search employee, role, skill..."
              value={searchQuery}
              onChange={setSearchQuery}
            />

            <select
              data-testid="status-filter-select"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              style={{
                background: colors.panel,
                color: colors.text,
                border: `1px solid ${colors.border}`,
                borderRadius: spacing.xs,
                padding: `${spacing.xs}px ${spacing.sm}px`,
                fontSize: typography.size.xs,
              }}
            >
              {STATUS_FILTERS.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.label}
                </option>
              ))}
            </select>
          </div>
        ) : null}
      </div>

      {/* Tab Content Views */}
      {activeTab === "employees" ? (
        filteredEmployees.length === 0 ? (
          <EmptyState title="No digital employees found matching the filters" />
        ) : (
          <div
            data-testid="employees-grid"
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))",
              gap: spacing.md,
            }}
          >
            {filteredEmployees.map((emp) => (
              <EmployeeCard
                key={emp.employee_id}
                employee={emp}
                onInspect={handleInspectEmployee}
                onChat={handleOpenChat}
                onAssign={handleOpenAssignTask}
                onDelegateProject={handleOpenDelegateProject}
              />
            ))}
          </div>
        )
      ) : null}

      {activeTab === "board" ? (
        <WorkforceBoardView
          board={board}
          onSelectTask={handleSelectTask}
          onRequestApproval={handleRequestApproval}
        />
      ) : null}

      {activeTab === "activities" ? <ActivityFeedView activities={activities} /> : null}

      {/* Employee Detail Modal */}
      <EmployeeDetailModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        employee={selectedEmployee}
      />

      {/* Assign Task Modal */}
      <AssignTaskModal
        isOpen={isAssignModalOpen}
        onClose={() => setIsAssignModalOpen(false)}
        employees={employees}
        preselectedEmployee={assignPreselectedEmployee}
        onTaskAssigned={() => loadData()}
      />

      {/* Delegate Project / Mission Modal */}
      <DelegateProjectModal
        isOpen={isDelegateModalOpen}
        onClose={() => setIsDelegateModalOpen(false)}
        onDelegate={handleDelegateMission}
        isSubmitting={isSubmittingMission}
      />

      {/* Mission Detail Modal */}
      <MissionDetailModal
        isOpen={isMissionDetailModalOpen}
        onClose={() => setIsMissionDetailModalOpen(false)}
        mission={activeMission}
      />

      {/* Employee Chat Modal */}
      <EmployeeChatModal
        isOpen={isChatModalOpen}
        onClose={() => setIsChatModalOpen(false)}
        employee={chatEmployee}
        conversations={conversations}
        onUpdateConversation={handleUpdateConversation}
      />

      {/* Task Detail Modal */}
      <TaskDetailModal
        isOpen={isTaskDetailModalOpen}
        onClose={() => setIsTaskDetailModalOpen(false)}
        task={selectedTask}
        onRequestApproval={handleRequestApproval}
        onTaskExecuted={() => loadData()}
      />

      {/* Chief Approval & Release Modal */}
      <ChiefApprovalModal
        isOpen={isApprovalModalOpen}
        onClose={() => setIsApprovalModalOpen(false)}
        workItem={approvingTask}
        onReleased={() => loadData()}
      />
    </div>
  );
}

