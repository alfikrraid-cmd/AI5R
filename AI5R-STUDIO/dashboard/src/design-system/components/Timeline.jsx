import Panel from "./Panel";

const DEFAULT_ACTIVITIES = [
  "10:01 👁 Reality detected",
  "10:02 🧠 Brain analyzed",
  "10:03 🤖 Employee assigned",
  "10:04 ⚡ Action executed",
  "10:05 💾 Experience stored",
  "10:06 🌱 Learning updated",
];

export default function Timeline({ activities = DEFAULT_ACTIVITIES, title = "Realtime Timeline" }) {
  return (
    <Panel>
      <h2>{title}</h2>

      {activities.map((activity, index) => (
        <p key={index}>{activity}</p>
      ))}
    </Panel>
  );
}
