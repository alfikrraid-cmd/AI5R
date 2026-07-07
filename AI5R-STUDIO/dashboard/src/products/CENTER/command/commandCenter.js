import {
    getProductIntelligence
}
from "../intelligence/productIntelligence";



export function getCommandCenter(){


    const intelligence =
    getProductIntelligence();



    return {


        platform:
        "AI5R PRODUCT COMMAND CENTER",


        status:
        "ONLINE",


        products:
        intelligence.total,


        active:
        intelligence.active,


        building:
        intelligence.building,


        health:
        intelligence.health


    };

}
