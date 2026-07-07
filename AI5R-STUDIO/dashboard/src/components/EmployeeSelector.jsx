function EmployeeSelector({ employees, selectedEmployee, onSelect }) {
    return (
        <div className="card">
            <h2>Digital Employee</h2>

            <select
                value={selectedEmployee}
                onChange={(event) => onSelect(event.target.value)}
            >
                {employees.map((employee) => (
                    <option key={employee.id} value={employee.id}>
                        {employee.name} — {employee.role}
                    </option>
                ))}
            </select>
        </div>
    );
}

export default EmployeeSelector;
