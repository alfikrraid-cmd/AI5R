import { AI5R_PRODUCTS } 
from "../productRegistry";


import { PRODUCT_LIFECYCLE }
from "../lifecycle/productLifecycle";


export function getProductIntelligence(){


    return {

        total:
        AI5R_PRODUCTS.length,


        active:
        PRODUCT_LIFECYCLE.filter(

            item =>
            item.stage === "ACTIVE"

        ).length,


        building:
        PRODUCT_LIFECYCLE.filter(

            item =>
            item.stage === "BUILDING"

        ).length,


        planned:
        PRODUCT_LIFECYCLE.filter(

            item =>
            item.stage === "PLANNED"

        ).length,


        health:
        "GOOD"

    };

}
