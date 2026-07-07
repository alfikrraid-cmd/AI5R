export class DemoAnalytics{


    constructor(){

        this.events = [];

    }



    track(
        event
    ){

        this.events.push({

            event,

            timestamp:
            new Date()
            .toISOString()

        });


        return {

            status:
            "TRACKED"

        };

    }



    summary(){

        return {

            total_events:
            this.events.length

        };

    }

}
