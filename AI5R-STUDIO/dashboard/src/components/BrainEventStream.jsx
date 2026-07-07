import { useEffect, useState } from "react";
import { getBrainEvents } from "../api/brainClient";

function BrainEventStream() {
    const [events, setEvents] = useState([]);

    useEffect(() => {
        getBrainEvents().then(setEvents);
    }, []);

    return (
        <div className="card">
            <h2>Brain Event Stream</h2>

            <div className="brain-event-stream">
                {events.map((event, index) => (
                    <div key={index} className="brain-event">
                        <strong>{event.event}</strong>
                        <span>{event.module} · {event.employee_id}</span>
                        <small>{event.status}</small>
                        <p>{event.message}</p>
                    </div>
                ))}
            </div>
        </div>
    );
}

export default BrainEventStream;
