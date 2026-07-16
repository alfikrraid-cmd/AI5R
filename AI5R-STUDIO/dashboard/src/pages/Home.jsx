import { Link } from "react-router-dom";

export default function Home() {
    return (
        <div>
            <h1>Welcome to AI5R Studio</h1>

            <p>
                One Root. Many Branches. Infinite Intelligence.
            </p>

            <Link to="/ltsa">
                Open LTSA →
            </Link>
        </div>
    );
}