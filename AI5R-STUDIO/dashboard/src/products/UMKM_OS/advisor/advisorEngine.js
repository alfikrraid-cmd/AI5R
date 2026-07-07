export function askAdvisor(question){


    if(
        question
        .toLowerCase()
        .includes("turun")
    ){

        return {

            insight:
            "Sales performance declining",

            recommendation:
            "Run retention campaign and optimize best selling products",

            priority:
            "HIGH"

        };

    }


    return {

        insight:
        "Business condition stable",

        recommendation:
        "Continue optimization",

        priority:
        "MEDIUM"

    };

}
