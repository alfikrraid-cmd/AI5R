export function simulateBusinessConversation(
    question
){

    if(
        question
        .toLowerCase()
        .includes("omzet")
        ||
        question
        .toLowerCase()
        .includes("turun")
    ){

        return {

            analysis:
            "Customer engagement has decreased.",

            priority:
            "HIGH",

            actions:[

                "Contact existing customers",

                "Create retention campaign",

                "Optimize best selling products"

            ]

        };

    }


    return {

        analysis:
        "Business condition is stable.",

        priority:
        "MEDIUM",

        actions:[

            "Continue monitoring"

        ]

    };

}
