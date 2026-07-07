import {
    getExecutiveData
}
from "../executive/executiveData";



export default function ExecutiveDashboard(){


    const data =
    getExecutiveData();



    return (

        <div className="card">


            <h2>
                👔 Executive Dashboard
            </h2>


            <p>
                Revenue:
                {" "}
                {data.revenue}
            </p>


            <p>
                Customers:
                {" "}
                {data.customers}
            </p>


            <p>
                Growth:
                {" "}
                {data.growth}
            </p>


            <p>
                Risk:
                {" "}
                {data.risk}
            </p>


            <p>
                AI Recommendation:
                {" "}
                {data.recommendation}
            </p>


        </div>

    );

}
