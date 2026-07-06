export default function StatusCard({
    title,
    value
}){

    return (

        <div className="card">

            <h3>{title}</h3>

            <strong>{value}</strong>

        </div>

    );

}
