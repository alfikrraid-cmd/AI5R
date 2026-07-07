function TaskQueue({ tasks }) {
    return (
        <div className="card">
            <h2>Task Queue</h2>

            <div className="task-list">
                {tasks.map((task) => (
                    <div key={task.id} className="task-item">
                        <strong>{task.id}</strong>
                        <span>{task.title}</span>
                        <small>{task.status}</small>
                    </div>
                ))}
            </div>
        </div>
    );
}

export default TaskQueue;
